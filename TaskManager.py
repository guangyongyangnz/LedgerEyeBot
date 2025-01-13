import asyncio


class TaskManager:
    def __init__(self):
        self.tasks = []

    def add_task(self, task):
        self.tasks.append(task)

    async def run_all(self):
        await asyncio.gather(*self.tasks)
