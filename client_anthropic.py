from anthropic import Anthropic

class CientAnthroipc:
    def __init__(self, model="claude-3-5-sonnet-20240620"):
        self.model = model
        self.client = Anthropic(api_key="YOUR KEY")

    def completion(self, **kwargs):
        return self.client.messages.create(
            model=self.model,
            **kwargs
        )