"""Pure synthetic-case projection; no private evidence or filesystem discovery."""
import hashlib
import json

from .files import encoded


def public_case(value):
    # Imported at call time: Store remains the only state and consent owner.
    from .store import TASK_INPUT_LIMIT, feedback_text, require, token

    require(isinstance(value, dict) and set(value) == {
        'case_id', 'language', 'purpose', 'inputs', 'outcome_contract', 'counterpart'}, 'case_fields')
    require(len(encoded(value)) <= TASK_INPUT_LIMIT, 'case_size')
    require(token(value['case_id']) and value['language'] in ('en', 'ko')
            and value['purpose'] in ('outcome', 'routing', 'adherence'), 'case_identity')

    def inputs(item):
        require(isinstance(item, dict) and set(item) == {'request', 'files'}, 'case_inputs')
        feedback_text(item['request'])
        require(isinstance(item['files'], dict) and len(item['files']) <= 16, 'case_files')
        for name, content in item['files'].items():
            require(isinstance(name, str) and 0 < len(name) <= 160 and '\\' not in name
                    and all(part not in ('', '.', '..') for part in name.split('/')), 'case_file_path')
            require(isinstance(content, str) and len(content.encode('utf-8')) <= 8192, 'case_file_size')

    def contract(item):
        require(isinstance(item, dict) and set(item) == {'required', 'forbidden'}, 'case_contract')
        for name in ('required', 'forbidden'):
            values = item[name]
            require(isinstance(values, list) and len(values) <= 16
                    and (name != 'required' or bool(values)), 'case_contract')
            for text in values:
                feedback_text(text)

    inputs(value['inputs']); contract(value['outcome_contract'])
    counterpart = value['counterpart']
    require(isinstance(counterpart, dict) and set(counterpart) == {'inputs', 'outcome_contract'}, 'case_counterpart')
    inputs(counterpart['inputs']); contract(counterpart['outcome_contract'])
    result = json.loads(encoded(value))
    result.update(schema_version=1, classification='development', artifact_hashes={})
    for prefix, item in [('reproduction', result['inputs']), ('counterpart', result['counterpart']['inputs'])]:
        for name, content in item['files'].items():
            result['artifact_hashes'][prefix + '/' + name] = hashlib.sha256(content.encode('utf-8')).hexdigest()
    return result
