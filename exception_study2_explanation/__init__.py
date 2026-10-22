"""Matched explicit explanations, independent of the frozen native screen."""
VERSION = 'study2-current-qwen-explicit-explanation-v1'
SOURCE_ZIP = 'screen-evidence-20261022T214422Z.zip'
SOURCE_LOG = 'screen-run-20261022T214422Z.log'
SOURCE_SHA256 = 'bb0e059f8a44a69b33990998b672e245405c4ca67c2d7d9214113283a6c9d31a'
LOG_SHA256 = '0941eaab54b838e459e127caa53a7d7aa3cd6b25634778f309ab17738dc0b0a1'
SOURCE_PLAN = 'edda713e841caafcd34d86f299d60a07cbde93a1b3d563a27ecfd13b7a4f52f6'
SOURCE_CONTRACT = '701262504d095b23d2d3320fb1ec794647b55b1064c07bb9788eb8a4547b9998'
INSTRUCTION = ('Think step by step before answering. Write your reasoning, then put a '
               'single uppercase letter—A, B, or C—alone on the final line.')
ENVIRONMENT = {'VLLM_USE_FLASHINFER_SAMPLER': '0'}
STOP = 'STOP_AFTER_96_EXPLANATIONS_NO_AUTOMATIC_EXPANSION'
