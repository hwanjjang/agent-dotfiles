"""Closed native-routing metadata grammar; synthetic bytes, no client execution."""
import hashlib
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/improvement'))
import native_trial_plan as plan


class RoutingMetadataTests(unittest.TestCase):
    def validate(self, header, description='Useful work.', name='first'):
        sources = [(name, header, description)] + [
            (n, f'---\nname: {n}\ndescription: Useful work.\n---\nBody\n', 'Useful work.')
            for n in ('second', 'third')]
        self.validate_sources(sources)

    def validate_sources(self, sources):
        rows, selected = [], {}
        for slot, (name, text, description) in enumerate(sources):
            data = text.encode();resource = f'skills/{name}/SKILL.md'
            selected['bundle', resource] = data
            rows.append(dict(slot=slot, name=name, main_resource=resource,
                             main_sha256=hashlib.sha256(data).hexdigest(),
                             description_sha256=hashlib.sha256(description.encode()).hexdigest()))
        value = dict(mode='natural', observer='implicit-stderr-json-v1',
                     catalog_scope='declared_experiment_subset',
                     catalog_digest=plan.digest(rows), catalog=rows)
        plan.validate_routing(value, selected)

    def refused(self, header, description='Useful work.', name='first'):
        with self.assertRaisesRegex(plan.Refusal, '^routing_metadata$'):
            self.validate(header, description, name)

    def test_description_suffix_is_not_a_delimiter(self):
        self.validate('---\nname: first\ndescription: Real---\n---\nBody\n', 'Real---')

    def test_suffix_cannot_hide_later_disable_or_bind_truncated_description(self):
        text = '---\nname: first\ndescription: Real---\ndisable-model-invocation: true\n---\nBody\n'
        for description in ('Real', 'Real---'):
            with self.subTest(description=description):self.refused(text, description)

    def test_nonliteral_key_spellings_and_unknown_fields_refuse(self):
        for key in ('"disable-model-invocation"', "'disable-model-invocation'",
                    'disable-model-invocation ', ' disable-model-invocation',
                    'disable-model-invocation\t', 'unknown'):
            with self.subTest(key=key):
                self.refused(f'---\nname: first\ndescription: Useful work.\n{key}: true\n---\n')
        for line in ('"name": first', 'name : first', 'name:first'):
            with self.subTest(line=line):
                self.refused(f'---\n{line}\ndescription: Useful work.\n---\n')

    def test_plain_typed_flow_and_indicator_values_refuse(self):
        values = ('true','False','NULL','~','yes','NO','on','off','y','N',
                  '123','-12','+1','1.5','1e3','0x10','0o12','.inf','.NaN',
                  '2026-10-19','[a, b]','{x: y}','%directive','@value','`value',
                  '> text','| text',"'quoted'",'&anchor','*alias','!tag','? value',
                  '- value',': value','text # comment','text: nested')
        for raw in values:
            with self.subTest(raw=raw):
                self.refused(f'---\nname: first\ndescription: {raw}\n---\n',raw)
        self.refused('---\nname: 123\ndescription: Useful work.\n---\n',name='123')

    def test_json_strings_are_strings_and_boolean_controls_are_typed(self):
        for text in ('true','123','[a, b]','Text: details # literal','한글 설명'):
            self.validate(f'---\nname: "first"\ndescription: {json.dumps(text)}\n'
                          'disable-model-invocation: false\nuser-invocable: true\n---\n',text)
        for key, values in [('disable-model-invocation',('true','"false"','False','null','[]')),
                            ('user-invocable',('"true"','True','null','[]'))]:
            for raw in values:
                with self.subTest(key=key,raw=raw):
                    self.refused(f'---\nname: first\ndescription: Useful work.\n{key}: {raw}\n---\n')
        self.validate('---\nname: first\ndescription: Useful work.\nuser-invocable: false\n---\n')

    def test_duplicate_control_fields_and_missing_exact_delimiter_refuse(self):
        for extra in ('user-invocable: true\nuser-invocable: false\n',
                      'disable-model-invocation: false\ndisable-model-invocation: false\n',
                      'name: first\n','description: Useful work.\n'):
            with self.subTest(extra=extra):
                self.refused('---\nname: first\ndescription: Useful work.\n'+extra+'---\n')
        self.refused('---\nname: first\ndescription: Useful work.---\nBody\n', 'Useful work.')

    def test_non_lf_line_boundaries_and_json_non_strings_refuse(self):
        for separator in ('\r', '\v', '\f', '\x85', '\u2028', '\u2029'):
            with self.subTest(separator=repr(separator)):
                self.refused('---\nname: first\ndescription: Useful work.'+separator+'---\n')
        for raw in ('""', '"line\\nnext"', '"text" # comment', '"unterminated'):
            with self.subTest(raw=raw):
                self.refused(f'---\nname: first\ndescription: {raw}\n---\n', raw)

    def test_raw_control_characters_are_not_plain_string_metadata(self):
        for control in ('\x00','\x01','\x1f'):
            value='Useful'+control+'work'
            with self.subTest(control=repr(control)):
                self.refused(f'---\nname: first\ndescription: {value}\n---\n',value)

    def test_raw_value_tabs_refuse_but_separator_tabs_remain_supported(self):
        for value in ('Useful\twork', 'Useful work.\t'):
            with self.subTest(value=repr(value)):
                self.refused(f'---\nname: first\ndescription: {value}\n---\n', value.strip())
        self.validate('---\nname:\tfirst\ndescription:\tUseful work.\n---\n')

    def test_decoded_json_controls_and_line_separators_refuse(self):
        for control in ('\x00', '\t', '\n', '\r', '\x1f', '\x7f', '\x80', '\x85', '\x9f', '\u2028', '\u2029'):
            value='Useful'+control+'work'
            with self.subTest(control=repr(control)):
                self.refused(f'---\nname: first\ndescription: {json.dumps(value)}\n---\n', value)

    def test_all_four_maintained_skill_headers_are_supported(self):
        root = Path(__file__).resolve().parents[1]
        sources = []
        for name in ('to-spec','planning-and-task-breakdown','to-tickets','issue-writing'):
            text = (root/'skills'/name/'SKILL.md').read_text()
            line = next(line for line in text.splitlines() if line.startswith('description: '))
            raw = line[len('description: '):]
            description = json.loads(raw) if raw.startswith('"') else raw
            sources.append((name,text,description))
        self.validate_sources(sources)

    def test_json_surrogate_escape_pairs_refuse_native_yaml_incompatibility(self):
        for raw in (r'"\ud83d\ude00"', r'"\uD83D\uDE00"',
                    r'"\ud800\udc00"', r'"\udbff\udfff"',
                    r'"\\\ud83d\ude00"'):
            with self.subTest(raw=raw):
                self.refused(f'---\nname: first\ndescription: {raw}\n---\n',
                             json.loads(raw))

    def test_utf8_bmp_and_literal_backslash_unicode_spelling_remain_supported(self):
        values = [('"Useful 😀 work"', 'Useful 😀 work'),
                  (r'"\ud55c\uae00 \u263a"', '한글 ☺'),
                  (r'"\ud7ff\ue000"', '\ud7ff\ue000')]
        for text in (r'\ud83d\ude00', r'\\ud800', r'\uDFFF literal',
                     r'ordinary \\ text'):
            values.append((json.dumps(text), text))
        for raw, text in values:
            with self.subTest(raw=raw):
                self.validate(f'---\nname: first\ndescription: {raw}\n---\n', text)


if __name__ == '__main__':unittest.main()
