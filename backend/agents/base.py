from abc import ABC, abstractmethod

class Agent(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    async def run(self, task, ctx: dict):
        pass
