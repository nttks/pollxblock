import datetime
import json
import logging
from mock import Mock, patch
from nose.tools import (
    assert_equals, assert_true, assert_false,
    assert_in, assert_regexp_matches, assert_raises
)
import re
import StringIO
from webob import Request

from workbench.runtime import WorkbenchRuntime
from xblock.runtime import KvsFieldData, DictKeyValueStore
from pollxblock.pollxblock import PollXBlock, UpdateFromXmlError, _str2bool


# Silence too verbose Django logging
logging.disable(logging.DEBUG)


IMPORT_XML = """\
<pollxblock display_name="Test Poll XBlock" reset="True">
  <question>Did you enjoy import?</question>
  <answers>
    <answer id="one">ONE</answer>
    <answer id="two">TWO</answer>
  </answers>
</pollxblock>\
"""


def make_request(body):
    request = Request.blank('/')
    request.method = 'POST'
    request.body = body.encode('utf-8')
    return request


def make_block():
    runtime = WorkbenchRuntime()
    key_store = DictKeyValueStore()
    db_model = KvsFieldData(key_store)
    return PollXBlock(runtime, db_model, Mock())


def parse_xml_to_block(runtime, xml):
    """A helper to get a block from some XML."""

    # WorkbenchRuntime has an id_generator, but most runtimes won't
    # (because the generator will be contextual), so we
    # pass it explicitly to parse_xml_string.
    usage_id = runtime.parse_xml_string(xml, runtime.id_generator)
    block = runtime.get_block(usage_id)
    return block


def export_xml_for_block(runtime, block):
    """A helper to return the XML string for a block."""
    output = StringIO.StringIO()
    runtime.export_to_xml(block, output)
    return output.getvalue()


def squish(text):
    """Squish here document to compare."""
    return re.sub('\n +', '', text.strip())


def test_templates_contents():
    block = make_block()
    block.display_name = 'Test Poll XBlock'

    student_fragment = block.render('student_view', Mock())
    assert_in('<div class="poll_question">', student_fragment.content)

    studio_fragment = block.render('studio_view', Mock())
    assert_in(
        '<div class="wrapper-comp-settings is-active editor-with-buttons" id="settings-tab">',
        studio_fragment.content)


def test_get_state():
    block = make_block()

    data = json.dumps({})
    res = json.loads(block.handle('get_state', make_request(data)).body)
    assert_equals(res, {
        'poll_answer': '',
        'poll_answers': {},
        'total': 0,
    })


def test_answer_poll():
    block = make_block()
    block.poll_answers = {'one': 0}

    data = json.dumps({'poll_answer': 'one'})
    res = json.loads(block.handle('answer_poll', make_request(data)).body)
    assert_equals(res, {
        'poll_answers': {'one': 1},
        'total': 1,
        'callback': {'objectName': 'Conditional'},
    })


def test_answer_poll_when_voted_is_true():
    block = make_block()
    block.poll_answer = 'one'
    block.poll_answers = {'one': 1}
    block.voted = True

    data = json.dumps({'poll_answer': 'one'})
    res = json.loads(block.handle('answer_poll', make_request(data)).body)
    assert_equals(res, {'error': 'Unknown Command!'})


def test_reset_poll():
    block = make_block()
    block.poll_answer = 'one'
    block.poll_answers = {'one': 1}
    block.voted = True
    block.reset = True

    data = json.dumps({})
    res = json.loads(block.handle('reset_poll', make_request(data)).body)
    assert_equals(res, {'status': 'success'})


def test_reset_poll_when_voted_is_false():
    block = make_block()
    block.poll_answer = 'one'
    block.poll_answers = {'one': 1}
    block.voted = False
    block.reset = True

    data = json.dumps({})
    res = json.loads(block.handle('reset_poll', make_request(data)).body)
    assert_equals(res, {'error': 'Unknown Command!'})


def test_save_edit():
    block = make_block()

    data = json.dumps({
        'display_name': 'Test Poll XBlock',
        'question': 'Do you enjoy tests?',
        'answerIds': ['one', 'two'],
        'answerTexts': ['ONE', 'TWO'],
        'reset': True,
    })
    res = block.handle('save_edit', make_request(data))
    assert_equals(json.loads(res.body), {'result': 'success'})

    assert_equals(block.display_name, 'Test Poll XBlock')
    assert_equals(block.question, 'Do you enjoy tests?')
    assert_equals(block.answers, [
        {'id': 'one', 'text': 'ONE'},
        {'id': 'two', 'text': 'TWO'},
    ])
    assert_equals(block.reset, True)


def test_parse_xml():
    runtime = WorkbenchRuntime()

    block = parse_xml_to_block(runtime, IMPORT_XML)

    assert_equals(block.display_name, 'Test Poll XBlock')
    assert_equals(block.question, 'Did you enjoy import?')
    assert_equals(block.answers, [{'id': 'one', 'text': 'ONE'}, {'id': 'two', 'text': 'TWO'}])
    assert_equals(block.reset, True)


def test_parse_xml_with_variations():
    runtime = WorkbenchRuntime()

    # root element has no 'display_name' attrib
    with assert_raises(UpdateFromXmlError) as cm:
        parse_xml_to_block(runtime, """\
            <pollxblock reset="True">
              <question>Did you enjoy import?</question>
              <answers>
                <answer id="one">ONE</answer>
                <answer id="two">TWO</answer>
              </answers>
            </pollxblock>\
        """)
    ex = cm.exception
    assert_equals(str(ex), 'Every "pollxblock" element must contain a "display_name" attribute.')

    # root element has no 'reset' attrib
    block = parse_xml_to_block(runtime, """\
        <pollxblock display_name="Test Poll XBlock">
          <question>Did you enjoy import?</question>
          <answers>
            <answer id="one">ONE</answer>
            <answer id="two">TWO</answer>
          </answers>
        </pollxblock>\
    """)
    assert_equals(block.reset, False)

    # root element has no 'question' element
    with assert_raises(UpdateFromXmlError) as cm:
        parse_xml_to_block(runtime, """\
            <pollxblock display_name="Test Poll XBlock" reset="True">
              <answers>
                <answer id="one">ONE</answer>
                <answer id="two">TWO</answer>
              </answers>
            </pollxblock>\
        """)
    ex = cm.exception
    assert_equals(str(ex), 'Every pollxblock must contain a "question" element.')

    # root element has no 'answers' element
    with assert_raises(UpdateFromXmlError) as cm:
        parse_xml_to_block(runtime, """\
            <pollxblock display_name="Test Poll XBlock" reset="True">
              <question>Did you enjoy import?</question>
            </pollxblock>\
        """)
    ex = cm.exception
    assert_equals(str(ex), 'Every pollxblock must contain a "answers" element.')

    # 'answer' element has no 'id' attrib
    with assert_raises(UpdateFromXmlError) as cm:
        parse_xml_to_block(runtime, """\
            <pollxblock display_name="Test Poll XBlock" reset="True">
              <question>Did you enjoy import?</question>
              <answers>
                <answer>ONE</answer>
                <answer>TWO</answer>
              </answers>
            </pollxblock>\
        """)
    ex = cm.exception
    assert_equals(str(ex), 'Every "answer" element must contain a "id" attribute.')


def test_add_xml_to_node():
    runtime = WorkbenchRuntime()

    block = parse_xml_to_block(runtime, IMPORT_XML)
    export_xml = export_xml_for_block(runtime, block)
    assert_equals(export_xml, squish("""\
        <?xml version='1.0' encoding='UTF8'?>\n
        <pollxblock display_name="Test Poll XBlock" reset="True">
          <question>Did you enjoy import?</question>
          <answers>
            <answer id="one">ONE</answer>
            <answer id="two">TWO</answer>
          </answers>
        </pollxblock>\
    """))


def test_str2bool():
    assert_true(_str2bool('TRUE'))
    assert_true(_str2bool('True'))
    assert_true(_str2bool('true'))
    assert_true(_str2bool('Yes'))
    assert_true(_str2bool('yes'))

    assert_true(_str2bool(u'TRUE'))
    assert_true(_str2bool(u'True'))
    assert_true(_str2bool(u'true'))
    assert_true(_str2bool(u'Yes'))
    assert_true(_str2bool(u'yes'))

    assert_false(_str2bool('FALSE'))
    assert_false(_str2bool('False'))
    assert_false(_str2bool('false'))
    assert_false(_str2bool('No'))
    assert_false(_str2bool('no'))

    assert_false(_str2bool(u'FALSE'))
    assert_false(_str2bool(u'False'))
    assert_false(_str2bool(u'false'))
    assert_false(_str2bool(u'No'))
    assert_false(_str2bool(u'no'))

    assert_true(_str2bool('Else', True))
    assert_false(_str2bool('Else', False))
    assert_false(_str2bool('Else'))

    assert_true(_str2bool(1, True))
    assert_false(_str2bool(1, False))
    assert_false(_str2bool(1))
