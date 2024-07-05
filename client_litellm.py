import litellm

class ClientLiteLLM:
    def __init__(self, model="anthropic.claude-3-5-sonnet-20240620-v1:0"):
        self.model = model


    def completion(self, **kwargs):
        return litellm.completion(
            model=self.model,
            **kwargs
        )



            

