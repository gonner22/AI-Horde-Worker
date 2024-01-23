"""Arg parsing for the main script."""
from worker.argparser.framework import arg_parser

arg_parser.add_argument(
    "--sfw",
    action="store_true",
    required=False,
    help="Set to true if you do not want this worker generating NSFW images.",
)
arg_parser.add_argument(
    "--blacklist",
    nargs="+",
    required=False,
    help="List the words that you want to blacklist.",
)
# arg_parser.add_argument(
#     "-m",
#     "--model",
#     action="store",
#     required=False,
#     help="Which model to run on this horde.",
# )
arg_parser.add_argument(
    "--kai_url",
    action="store",
    required=False,
    help="The URL in which the KoboldAI Client API can be found.",
)
arg_parser.add_argument(
    "--max_context_length",
    type=int,
    required=False,
    help="Set the max context for this scribe.",
)
arg_parser.add_argument(
    "--max_length",
    type=int,
    required=False,
    help="Set the max tokens for this scribe.",
)


args = arg_parser.parse_args()
