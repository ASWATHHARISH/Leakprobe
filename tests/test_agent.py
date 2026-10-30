import unittest
from types import SimpleNamespace as S
from leakprobe.agent import investigate

class Message:
    def __init__(self, content=None, calls=None):
        self.content, self.tool_calls = content, calls
    def model_dump(self, **kwargs):
        result = {'role':'assistant','content':self.content}
        if self.tool_calls:
            result['tool_calls'] = [{'id':x.id,'type':'function','function':{'name':x.function.name,'arguments':x.function.arguments}} for x in self.tool_calls]
        return result

class FakeClient:
    def __init__(self, messages):
        self.responses = iter(messages)
        self.requests = []
        self.chat = S(completions=S(create=self.create))
    def create(self, **kwargs):
        self.requests.append(kwargs)
        return S(choices=[S(message=next(self.responses),finish_reason='stop')],usage=None)

class AgentTests(unittest.TestCase):
    def test_tool_result_returns_to_model(self):
        call = S(id='c1',function=S(name='get_observations',arguments='{}'))
        client = FakeClient([Message(calls=[call]),Message(content='Need more evidence.')])
        result = investigate(client, 'test-model')
        self.assertEqual(result['status'],'completed')
        self.assertTrue(any(m['role']=='tool' for m in client.requests[-1]['messages']))
        self.assertIn('readings',result['trace'][0]['result'])

    def test_malformed_arguments_are_rejected(self):
        call = S(id='c1',function=S(name='get_observations',arguments='not json'))
        result = investigate(FakeClient([Message(calls=[call])]), 'test-model', max_rounds=1)
        self.assertEqual(result['status'],'budget_exhausted')
        self.assertIn('error',result['trace'][0]['result'])
