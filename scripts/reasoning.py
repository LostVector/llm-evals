"""Public reasoning policy metadata; unknown is deliberately distinct from unlimited."""
FIELDS = {
    'budget_tokens', 'budget_scope', 'budget_enforcement', 'budget_exhaustion',
    'final_answer_reserve_tokens', 'output_cap_includes_reasoning',
    'parser', 'chat_template_sha256', 'verification',
}
ENUMS = {
    'budget_scope': {'per_request', 'per_turn', 'unknown'},
    'budget_enforcement': {'server', 'client', 'none', 'unknown'},
    'budget_exhaustion': {'force_close_then_answer', 'stop_generation', 'none', 'unknown'},
    'verification': {'configured', 'observed', 'unknown'},
}


def reasoning_policy(value=None):
    """Validate a closed, sanitized schema. Null budget means unknown, -1 unlimited."""
    value = {} if value is None else value
    if not isinstance(value, dict) or set(value) - FIELDS:
        raise ValueError('Unknown reasoning policy fields')
    result = dict(budget_tokens=None, budget_scope='unknown', budget_enforcement='unknown',
                  budget_exhaustion='unknown', final_answer_reserve_tokens=None,
                  output_cap_includes_reasoning=None, parser='unknown',
                  chat_template_sha256=None, verification='unknown')
    result.update(value)
    for field, choices in ENUMS.items():
        if result[field] not in choices:
            raise ValueError('Invalid reasoning '+field)
    for field, minimum in [('budget_tokens', -1), ('final_answer_reserve_tokens', 0)]:
        item = result[field]
        if item is not None and (type(item) is not int or item < minimum):
            raise ValueError('Invalid reasoning '+field)
    if result['output_cap_includes_reasoning'] is not None and type(result['output_cap_includes_reasoning']) is not bool:
        raise ValueError('Invalid output cap accounting')
    import re
    if not isinstance(result['parser'], str) or not re.fullmatch(r'[A-Za-z0-9_.+ -]{1,80}', result['parser']):
        raise ValueError('Parser must be a public software label')
    digest = result['chat_template_sha256']
    if digest is not None and (not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest)):
        raise ValueError('Invalid chat template hash')
    return result


def request_parameters(config):
    """Explicit llama.cpp request override, separate from descriptive metadata."""
    params = config.get('reasoning_request', {})
    if not isinstance(params, dict) or set(params) - {'reasoning_budget_tokens'}:
        raise ValueError('Unsupported reasoning request parameter')
    if params:
        budget = params.get('reasoning_budget_tokens')
        if type(budget) is not int or budget < -1:
            raise ValueError('Invalid reasoning request budget')
        if reasoning_policy(config.get('reasoning'))['budget_tokens'] != budget:
            raise ValueError('Request budget must match recorded reasoning policy')
    return dict(params)
