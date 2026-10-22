"""Independent fixed-budget screen; historical native protocols are unchanged."""
VERSION = 'study2-current-qwen-native-screen-v1'
SEED = 2026102101
BUDGET = 4096
MODEL = 'Qwen/Qwen3.8-27B'
REVISION = '1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0'
SAMPLER = dict(n=1, temperature=1.0, top_p=0.95, top_k=20, min_p=0.0,
               presence_penalty=0.0, frequency_penalty=0.0, repetition_penalty=1.0)
ENGINE = dict(dtype='bfloat16', quantization=None, tensor_parallel_size=1,
              max_model_len=8192, max_num_seqs=1, max_num_batched_tokens=8192,
              gpu_memory_utilization=0.90, enable_prefix_caching=False,
              language_model_only=True, kv_cache_dtype='auto', seed=SEED,
              generation_config='vllm', trust_remote_code=False)
RUNTIME = {'vllm':'0.26.0','torch':'2.11.0','transformers':'5.8.0',
           'tokenizers':'0.22.2','huggingface-hub':'1.7.1','jinja2':'3.1.6'}
STOP = 'STOP_CURRENT_SCREEN_NO_AUTOMATIC_FOLLOWUP'

SAMPLING_OPTIONS = dict(stop=[], min_tokens=0, ignore_eos=False, detokenize=False,
    skip_special_tokens=False, spaces_between_special_tokens=False, include_stop_str_in_output=False,
    thinking_token_budget=None, logprobs=None, prompt_logprobs=None, structured_outputs=None,
    logit_bias=None, allowed_token_ids=None, bad_words=[])
