FROM ubuntu:22.04

RUN mkdir /worker

WORKDIR /worker

COPY . .

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
        python3 \
        python3-pip \
        python3-venv \
        ffmpeg \
        libsm6 \
        libxext6 \
        bzip2 \
        wget \
        curl \
      && python3 -m venv /venv \
      && /bin/bash -c "source /venv/bin/activate && ./update-runtime.sh && pip cache purge" \
      && rm -rf /var/lib/apt/lists/*

EXPOSE 443

CMD ["bin/micromamba", "run", "-r", "conda", "-n", "linux", "python", "-s", "bridge_scribe.py"]
