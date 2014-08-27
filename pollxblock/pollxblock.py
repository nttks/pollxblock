"""PollXBlock is ungraded XBlock used by students to
to do set of polls.

On the client side we show:
If student does not yet anwered - Question with set of choices.
If student have answered - Question with statistics for each answers.
"""

import cgi
from collections import OrderedDict
import json
import logging
import lxml.etree as etree
import pkg_resources

from django.template import Context, Template

from xblock.core import XBlock
from xblock.fields import Boolean, Dict, List, Scope, String
from xblock.fragment import Fragment

log = logging.getLogger(__name__)


class PollXBlock(XBlock):
    """
    XBlock providing a set of polls
    """
    display_name = String(
        help="Name of the component in the edX platform",
        scope=Scope.settings,
        default="Poll XBlock"
    )

    voted = Boolean(
        help="Whether this student has voted on the poll",
        scope=Scope.user_state,
        default=False
    )

    poll_answer = String(
        help="Student answer",
        scope=Scope.user_state,
        default=''
    )

    poll_answers = Dict(
        help="All possible answers for the poll fro other students",
        scope=Scope.user_state_summary
    )

    question = String(
        help="Poll question",
        scope=Scope.content,
        default="Did you enjoy this video?"
    )

    # List of answers, in the form {'id': 'some id', 'text': 'the answer text'}
    answers = List(
        help="Poll answers",
        scope=Scope.content,
        default=[{'id': 'yes', 'text': 'Yes'}, {'id': 'no', 'text': 'No'}, {'id': 'no_opinion', 'text': 'No opinion'}]
    )

    reset = Boolean(
        help="Can reset/revote many time",
        scope=Scope.content,
        default=False
    )

    def resource_string(self, path):
        """Handy helper for getting resources from our kit."""
        data = pkg_resources.resource_string(__name__, path)
        return data.decode("utf8")

    def student_view(self, context=None):
        """
        The primary view of the PollXBlock, shown to students
        when viewing courses.
        """
        template = Template(self.resource_string("static/html/pollxblock.html"))
        html = template.render(Context({
            'configuration_json': self.dump_poll()
        }))
        frag = Fragment(html)
        frag.add_css(self.resource_string("static/css/pollxblock.css"))
        frag.add_javascript(self.resource_string("static/js/src/pollxblock.js"))
        frag.initialize_js('PollXBlock')
        return frag

    def dump_poll(self):
        """Dump poll information.

        Returns:
            string - Serialize json.
        """
        # FIXME: hack for resolving caching `default={}` during definition
        # poll_answers field
        if self.poll_answers is None:
            self.poll_answers = {}

        answers_to_json = OrderedDict()

        # FIXME: fix this, when xblock support mutable types.
        # Now we use this hack.
        temp_poll_answers = self.poll_answers

         # Fill self.poll_answers, prepare data for template context.
        for answer in self.answers:
            # Set default count for answer = 0.
            if answer['id'] not in temp_poll_answers:
                temp_poll_answers[answer['id']] = 0
            answers_to_json[answer['id']] = cgi.escape(answer['text'])
        self.poll_answers = temp_poll_answers

        return json.dumps({
            'answers': answers_to_json,
            'question': cgi.escape(self.question),
            # to show answered poll after reload:
            'poll_answer': self.poll_answer,
            'poll_answers': self.poll_answers if self.voted else {},
            'total': sum(self.poll_answers.values()) if self.voted else 0,
            'reset': str(self.reset).lower()
        })

    @XBlock.json_handler
    def get_state(self, data, suffix=''):
        """Handle Ajax to show the state of polls"""
        return {'poll_answer': self.poll_answer,
                'poll_answers': self.poll_answers,
                'total': sum(self.poll_answers.values())}

    @XBlock.json_handler
    def answer_poll(self, data, suffix=''):
        """Handle Ajax to post the answer"""
        if not self.voted:
            poll_answer = data['poll_answer']

            # FIXME: fix this, when xblock will support mutable types.
            # Now we use this hack.
            temp_poll_answers = self.poll_answers
            temp_poll_answers[poll_answer] += 1
            self.poll_answers = temp_poll_answers

            self.voted = True
            self.poll_answer = poll_answer
            return {'poll_answers': self.poll_answers,
                    'total': sum(self.poll_answers.values()),
                    'callback': {'objectName': 'Conditional'}}
        else:  # return error message
            return {'error': 'Unknown Command!'}

    @XBlock.json_handler
    def reset_poll(self, data, suffix=''):
        """Handle Ajax to change the vote"""
        if self.voted and self.reset:
            self.voted = False

            # FIXME: fix this, when xblock will support mutable types.
            # Now we use this hack.
            temp_poll_answers = self.poll_answers
            temp_poll_answers[self.poll_answer] -= 1
            self.poll_answers = temp_poll_answers

            self.poll_answer = ''
            return {'status': 'success'}
        else:  # return error message
            return {'error': 'Unknown Command!'}

    def studio_view(self, context=None):
        """
        The primary view of the PollXBlock, shown to teachers
        when editing the block.
        """
        template = Template(self.resource_string("static/html/pollxblock_edit.html"))

        #parameters sent to browser for edit html page
        html = template.render(Context({
            'display_name': self.display_name,
            'voted': self.voted,
            'poll_answer': self.poll_answer,
            'poll_answers': self.poll_answers,
            'answers': self.answers,
            'number_of_answers': len(self.answers),
            'question': self.question,
            'reset': self.reset
        }))

        frag = Fragment(html)
        frag.add_css(self.resource_string("static/css/pollxblock_edit.css"))
        frag.add_javascript(self.resource_string("static/js/src/pollxblock_edit.js"))
        frag.initialize_js('PollXBlockEdit')
        return frag

    @XBlock.json_handler
    def save_edit(self, data, suffix=''):
        """
        Handler which saves the json data into XBlock fields.
        """
        self.display_name = data['display_name']
        self.question = data['question']
        self.answers = [{'id': x[0], 'text': x[1]} for x in zip(data['answerIds'], data['answerTexts'])]
        self.reset = data['reset']

        return {'result': 'success'}

    @staticmethod
    def workbench_scenarios():
        """A canned scenario for display in the workbench."""
        return [
            ("PollXBlock",
             """<vertical_demo>
                <pollxblock/>
                <pollxblock/>
                </vertical_demo>
             """),
        ]

    @classmethod
    def parse_xml(cls, root, runtime, keys, id_generator):
        """Instantiate XBlock object from runtime XML definition.

        Inherited by XBlock core.

        Here is a sample of PollXBlock.

        <pollxblock url_name="db47ae70b9d3429abbd939e01f0661c3" display_name="Poll XBlock" reset="True">
          <question>Did you enjoy this video?</question>
          <answers>
            <answer id="yes">Yes</answer>
            <answer id="no">No</answer>
            <answer id="no_opinion">No opinion</answer>
          </answers>
        </pollxblock>
        """
        block = runtime.construct_xblock_from_class(cls, keys)

        # pollxblock.display_name
        if 'display_name' in root.attrib:
            display_name = unicode(root.get('display_name'))
        else:
            raise UpdateFromXmlError('Every "pollxblock" element must contain a "display_name" attribute.')

        # pollxblock.reset
        if 'reset' in root.attrib:
            reset = _str2bool(root.get('reset'), cls.reset.default)
        else:
            reset = cls.reset.default

        # pollxblock > question
        question_el = root.find('question')
        if question_el is None:
            raise UpdateFromXmlError('Every pollxblock must contain a "question" element.')
        else:
            question = _safe_get_text(question_el)

        # pollxblock > answers
        answers_el = root.find('answers')
        if answers_el is None:
            raise UpdateFromXmlError('Every pollxblock must contain a "answers" element.')

        # pollxblock > answers > answer
        answers = []
        for answer_el in answers_el.findall('answer'):
            answer_dict = dict()
            # pollxblock > answers > answer.id
            if 'id' in answer_el.attrib:
                answer_dict['id'] = unicode(answer_el.get('id'))
            else:
                raise UpdateFromXmlError('Every "answer" element must contain a "id" attribute.')
            answer_dict['text'] = _safe_get_text(answer_el)
            answers.append(answer_dict)

        # If we've gotten this far, then we've successfully parsed the XML
        # and validated the contents.  At long last, we can safely update the XBlock.
        block.display_name = display_name
        block.question = question
        block.answers = answers
        block.reset = reset

        return block

    def add_xml_to_node(self, root):
        """
        Serialize the XBlock to XML for exporting.
        """
        root.tag = 'pollxblock'

        if self.display_name is not None:
            root.set('display_name', unicode(self.display_name))

        if self.reset:
            root.set('reset', unicode(self.reset))

        # question
        question_el = etree.SubElement(root, 'question')
        question_el.text = unicode(self.question)

        # answers
        answers_el = etree.SubElement(root, 'answers')
        for answer in self.answers:
            answer_el = etree.SubElement(answers_el, 'answer')
            answer_el.set('id', unicode(answer['id']))
            answer_el.text = unicode(answer['text'])


class UpdateFromXmlError(Exception):
    """
    Error occurred while deserializing the OpenAssessment XBlock content from XML.
    """
    pass


def _safe_get_text(element):
    """
    Retrieve the text from the element, safely handling empty elements.

    Args:
        element (lxml.etree.Element): The XML element.

    Returns:
        unicode
    """
    return unicode(element.text) if element.text is not None else u""


def _str2bool(s, default=False):
    """
    Convert String to Boolean

    Args:
        s (String): String to be converted.
        default (Boolean): If s conforms to none of the keywords(True/Yes/False/No), returns default

    Returns:
        'True'  => True
        'true'  => True
        'Yes'   => True
        'yes'   => True
        'False' => False
        'false' => False
        'No'    => False
        'no'    => False
    """
    if isinstance(s, (str, unicode)):
        if s.lower() in ['true', 'yes']:
            return True
        elif s.lower() in ['false', 'no']:
            return False
    return default
