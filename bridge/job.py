import base64
import json
import sys
import time
import threading

from base64 import binascii
from io import BytesIO
import requests
from PIL import Image, UnidentifiedImageError
from nataili.util.cache import torch_gc
from nataili.util import logger
from nataili.inference.compvis import CompVis
from nataili.inference.diffusers.inpainting import inpainting
from bridge import JobStatus
from bridge import disable_voodoo

class HordeJob:
    retry_interval = 1
    def __init__(self, mm, bd):
        self.model_manager = mm
        self.bd = bd
        self.current_id = None
        self.current_payload = None
        self.current_generation = None
        self.loop_retry = 0
        self.status = JobStatus.INIT
        self.skipped_info = None
        thread = threading.Thread(target=self.start_job, args=())
        thread.daemon = True
        thread.start()

    def is_finished(self):
        if self.status in [JobStatus.WORKING, JobStatus.POLLING, JobStatus.INIT]:
            return(False)
        else:
            return(True)

    def is_polling(self):
        if self.status in [JobStatus.POLLING]:
            return(True)
        else:
            return(False)

    def is_finalizing(self):
        '''True if generation has finished even if upload is still remaining
        '''
        if self.status in [JobStatus.FINALIZING]:
            return(True)
        else:
            return(False)

    def delete(self):
        del self

    def prep_for_pop(self):
        self.skipped_info = None
        self.status = JobStatus.POLLING

    def start_job(self):
        while True:
            # Pop new request from the Horde
            if self.is_finished():
                break
            if self.loop_retry > 10 and self.current_id:
                logger.error(f"Exceeded retry count {self.loop_retry} for generation id {self.current_id}. Aborting generation!")
                self.status = JobStatus.FAULTED
                break
            elif self.current_id:
                logger.debug(f"Retrying ({self.loop_retry}/10) for generation id {self.current_id}...")
            available_models = self.model_manager.get_loaded_models_names()
            if "LDSR" in available_models:
                logger.warning("LDSR is an upscaler and doesn't belond in the model list. Ignoring")
                available_models.remove("LDSR")
            if "safety_checker" in available_models:
                available_models.remove("safety_checker")
            gen_dict = {
                "name": self.bd.worker_name,
                "max_pixels": self.bd.max_pixels,
                "priority_usernames": self.bd.priority_usernames,
                "nsfw": self.bd.nsfw,
                "blacklist": self.bd.blacklist,
                "models": available_models,
                "allow_img2img": self.bd.allow_img2img,
                "allow_painting": self.bd.allow_painting,
                "allow_unsafe_ip": self.bd.allow_unsafe_ip,
                "bridge_version": 6,
            }
            # logger.debug(gen_dict)
            self.headers = {"apikey": self.bd.api_key}
            if self.current_id:
                self.loop_retry += 1
            else:
                self.prep_for_pop()
                try:
                    pop_req = requests.post(
                        self.bd.horde_url + "/api/v2/generate/pop",
                        json=gen_dict,
                        headers=self.headers,
                        timeout=10,
                    )
                    logger.debug(f"Job pop took {pop_req.elapsed.total_seconds()}")
                except requests.exceptions.ConnectionError:
                    logger.warning(f"Server {self.bd.horde_url} unavailable during pop. Waiting 10 seconds...")
                    time.sleep(10)
                    continue
                except TypeError:
                    logger.warning(f"Server {self.bd.horde_url} unavailable during pop. Waiting 2 seconds...")
                    time.sleep(2)
                    continue
                except requests.exceptions.ReadTimeout:
                    logger.warning(f"Server {self.bd.horde_url} timed out during pop. Waiting 2 seconds...")
                    time.sleep(2)
                    continue
                try:
                    pop = pop_req.json()
                except json.decoder.JSONDecodeError:
                    logger.error(
                        f"Could not decode response from {self.bd.horde_url} as json. Please inform its administrator!"
                    )
                    time.sleep(self.retry_interval)
                    continue
                if pop is None:
                    logger.error(f"Something has gone wrong with {self.bd.horde_url}. Please inform its administrator!")
                    time.sleep(self.retry_interval)
                    continue
                if not pop_req.ok:
                    logger.warning(
                        f"During gen pop, server {self.bd.horde_url} responded with status code {pop_req.status_code}: "
                        f"{pop['message']}. Waiting for 10 seconds..."
                    )
                    if "errors" in pop:
                        logger.warning(f"Detailed Request Errors: {pop['errors']}")
                    time.sleep(10)
                    continue
                if not pop.get("id"):
                    job_skipped_info = pop.get("skipped")
                    if job_skipped_info and len(job_skipped_info):
                        self.skipped_info = f" Skipped Info: {job_skipped_info}."
                    else:
                        self.skipped_info = ""
                    # logger.info(f"Server {self.bd.horde_url} has no valid generations to do for us.{self.skipped_info}")
                    time.sleep(self.retry_interval)
                    continue
                self.current_id = pop["id"]
                self.current_payload = pop["payload"]
            self.status = JobStatus.WORKING
            # Generate Image
            model = pop.get("model", available_models[0])
            # logger.info([self.current_id,self.current_payload])
            use_nsfw_censor = self.current_payload.get("use_nsfw_censor", False)
            if self.bd.censor_nsfw and not self.bd.nsfw:
                use_nsfw_censor = True
            elif any(word in self.current_payload["prompt"] for word in self.bd.censorlist):
                use_nsfw_censor = True
            # use_gfpgan = self.current_payload.get("use_gfpgan", True)
            # use_real_esrgan = self.current_payload.get("use_real_esrgan", False)
            source_processing = pop.get("source_processing")
            source_image = pop.get("source_image")
            source_mask = pop.get("source_mask")
            # These params will always exist in the payload from the horde
            gen_payload = {
                "prompt": self.current_payload["prompt"],
                "height": self.current_payload["height"],
                "width": self.current_payload["width"],
                "seed": self.current_payload["seed"],
                "n_iter": 1,
                "batch_size": 1,
                "save_individual_images": False,
                "save_grid": False,
            }
            # These params might not always exist in the horde payload
            if "ddim_steps" in self.current_payload:
                gen_payload["ddim_steps"] = self.current_payload["ddim_steps"]
            if "sampler_name" in self.current_payload:
                gen_payload["sampler_name"] = self.current_payload["sampler_name"]
            if "cfg_scale" in self.current_payload:
                gen_payload["cfg_scale"] = self.current_payload["cfg_scale"]
            if "ddim_eta" in self.current_payload:
                gen_payload["ddim_eta"] = self.current_payload["ddim_eta"]
            if "denoising_strength" in self.current_payload and source_image:
                gen_payload["denoising_strength"] = self.current_payload["denoising_strength"]
            if self.current_payload.get("karras", False):
                gen_payload["sampler_name"] = gen_payload.get("sampler_name", "k_euler_a") + "_karras"
            # logger.debug(gen_payload)
            req_type = "txt2img"
            if source_image:
                img_source = None
                img_mask = None
                if source_processing == "img2img":
                    req_type = "img2img"
                elif source_processing == "inpainting":
                    req_type = "inpainting"
                if source_processing == "outpainting":
                    req_type = "outpainting"
            # Prevent inpainting from picking text2img and img2img gens (as those go via compvis pipelines)
            if model == "stable_diffusion_inpainting" and req_type not in [
                "inpainting",
                "outpainting",
            ]:
                # Try to find any other model to do text2img or img2img
                for m in available_models:
                    if m != "stable_diffusion_inpainting":
                        model = m
                # if the model persists as inpainting for text2img or img2img, we abort.
                if model == "stable_diffusion_inpainting":
                    # We remove the base64 from the prompt to avoid flooding the output on the error
                    if len(pop.get("source_image", "")) > 10:
                        pop["source_image"] = len(pop.get("source_image", ""))
                    if len(pop.get("source_mask", "")) > 10:
                        pop["source_mask"] = len(pop.get("source_mask", ""))
                    logger.error(
                        "Received an non-inpainting request for inpainting model. This shouldn't happen. "
                        f"Inform the developer. Current payload {pop}"
                    )
                    self.status = JobStatus.FAULTED
                    break
                    # TODO: Send faulted
            logger.debug(f"{req_type} ({model}) request with id {self.current_id} picked up. Initiating work...")
            try:
                safety_checker = (
                    self.model_manager.loaded_models["safety_checker"]["model"]
                    if "safety_checker" in self.model_manager.loaded_models
                    else None
                )
                if source_image:
                    base64_bytes = source_image.encode("utf-8")
                    img_bytes = base64.b64decode(base64_bytes)
                    img_source = Image.open(BytesIO(img_bytes))
                if source_mask:
                    base64_bytes = source_mask.encode("utf-8")
                    img_bytes = base64.b64decode(base64_bytes)
                    img_mask = Image.open(BytesIO(img_bytes))
                    if img_mask.size != img_source.size:
                        logger.warning(
                            f"Source image/mask mismatch. Resizing mask from {img_mask.size} to {img_source.size}"
                        )
                        img_mask = img_mask.resize(img_source.size)
            except KeyError:
                self.status = JobStatus.FAULTED
                break
            # If the received image is unreadable, we continue as text2img
            except UnidentifiedImageError:
                logger.error("Source image received for img2img is unreadable. Falling back to text2img!")
                req_type = "txt2img"
                if "denoising_strength" in gen_payload:
                    del gen_payload["denoising_strength"]
            except binascii.Error:
                logger.error(
                    "Source image received for img2img is cannot be base64 decoded (binascii.Error). "
                    "Falling back to text2img!"
                )
                req_type = "txt2img"
                if "denoising_strength" in gen_payload:
                    del gen_payload["denoising_strength"]
            if req_type in ["img2img", "txt2img"]:
                if req_type == "img2img":
                    gen_payload["init_img"] = img_source
                    if img_mask:
                        gen_payload["init_mask"] = img_mask
                generator = CompVis(
                    model=self.model_manager.loaded_models[model]["model"],
                    device=self.model_manager.loaded_models[model]["device"],
                    output_dir="bridge_generations",
                    load_concepts=True,
                    concepts_dir="models/custom/sd-concepts-library",
                    safety_checker=safety_checker,
                    filter_nsfw=use_nsfw_censor,
                    disable_voodoo=disable_voodoo.active,
                )
            else:
                # These variables do not exist in the outpainting implementation
                if "save_grid" in gen_payload:
                    del gen_payload["save_grid"]
                if "sampler_name" in gen_payload:
                    del gen_payload["sampler_name"]
                if "denoising_strength" in gen_payload:
                    del gen_payload["denoising_strength"]
                # We prevent sending an inpainting without mask or transparency, as it will crash us.
                if img_mask is None:
                    try:
                        red, green, blue, alpha = img_source.split()
                    except ValueError:
                        logger.warning("inpainting image doesn't have an alpha channel. Aborting gen")
                        self.status = JobStatus.FAULTED
                        break
                        # TODO: Send faulted
                gen_payload["inpaint_img"] = img_source
                if img_mask:
                    gen_payload["inpaint_mask"] = img_mask
                generator = inpainting(
                    self.model_manager.loaded_models[model]["model"],
                    self.model_manager.loaded_models[model]["device"],
                    "bridge_generations",
                    filter_nsfw=use_nsfw_censor,
                )
            try:
                generator.generate(**gen_payload)
                torch_gc()
            except RuntimeError:
                logger.error(
                    "Something went wrong when processing request. Probably an img2img error "
                    "Falling back to text2img to try and rescue this run.\n"
                    f"Please inform the developers of th below payload:\n{gen_payload}"
                )
                if "denoising_strength" in gen_payload:
                    del gen_payload["denoising_strength"]
                if "init_img" in gen_payload:
                    del gen_payload["init_img"]
                if "init_mask" in gen_payload:
                    del gen_payload["init_mask"]
                try:
                    generator.generate(**gen_payload)
                    torch_gc()
                except RuntimeError:
                    logger.error("Rescue Attempt also failed. Aborting!")
                    self.status = JobStatus.FAULTED
                    break
            # Submit back to horde
            # images, seed, info, stats = txt2img(**self.current_payload)
            buffer = BytesIO()
            # We send as WebP to avoid using all the horde bandwidth
            image = generator.images[0]["image"]
            seed = generator.images[0]["seed"]
            image.save(buffer, format="WebP", quality=90)
            # logger.info(info)
            # We unload the generator from RAM
            generator = None
            self.submit_dict = {
                "id": self.current_id,
                "generation": base64.b64encode(buffer.getvalue()).decode("utf8"),
                "api_key": self.bd.api_key,
                "seed": seed,
                "max_pixels": self.bd.max_pixels,
            }
            self.current_generation = seed
            # Not a daemon, so that it can survive after this class is garbage collected
            submit_thread = threading.Thread(target=self.submit_job, args=())
            submit_thread.start()
            if not self.current_generation:
                time.sleep(self.retry_interval)

    def submit_job(self):
        self.status = JobStatus.FINALIZING
        while self.is_finalizing():
            if self.loop_retry > 10:
                logger.error(f"Exceeded retry count {self.loop_retry} for generation id {self.current_id}. Aborting generation!")
                self.status = JobStatus.FAULTED
                break
            self.loop_retry += 1
            try:
                logger.debug(
                    f"posting payload with size of {round(sys.getsizeof(json.dumps(self.submit_dict)) / 1024,1)} kb"
                )
                submit_req = requests.post(
                    self.bd.horde_url + "/api/v2/generate/submit",
                    json=self.submit_dict,
                    headers=self.headers,
                    timeout=20,
                )
                logger.debug(f"Upload completed in {submit_req.elapsed.total_seconds()}")
                try:
                    submit = submit_req.json()
                except json.decoder.JSONDecodeError:
                    logger.error(
                        f"Something has gone wrong with {self.bd.horde_url} during submit. "
                        f"Please inform its administrator!  (Retry {self.loop_retry}/10)"
                    )
                    time.sleep(self.retry_interval)
                    continue
                if submit_req.status_code == 404:
                    logger.warning("The generation we were working on got stale. Aborting!")
                    self.status = JobStatus.FAULTED
                    break
                elif not submit_req.ok:
                    logger.warning(
                        f"During gen submit, server {self.bd.horde_url} "
                        f"responded with status code {submit_req.status_code}: "
                        f"{submit['message']}. Waiting for 10 seconds...  (Retry {self.loop_retry}/10)"
                    )
                    if "errors" in submit:
                        logger.warning(f"Detailed Request Errors: {submit['errors']}")
                    time.sleep(10)
                    continue
                logger.info(
                    f'Submitted generation with id {self.current_id} and contributed for {submit_req.json()["reward"]}'
                )
                self.status = JobStatus.DONE
                break
            except requests.exceptions.ConnectionError:
                logger.warning(
                    f"Server {self.bd.horde_url} unavailable during submit. Waiting 10 seconds...  (Retry {self.loop_retry}/10)"
                )
                time.sleep(10)
                continue
            except requests.exceptions.ReadTimeout:
                logger.warning(
                    f"Server {self.bd.horde_url} timed out during submit. Waiting 10 seconds...  (Retry {self.loop_retry}/10)"
                )
                time.sleep(10)
                continue
    