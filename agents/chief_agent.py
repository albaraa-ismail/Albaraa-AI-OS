from agents.research_agent import ResearchAgent
from agents.builder_agent import BuilderAgent
from agents.career_agent import CareerAgent
from agents.learning_agent import LearningAgent

class ChiefAgent:

    def __init__(self):
        self.research = ResearchAgent()
        self.builder = BuilderAgent()
        self.career = CareerAgent()
        self.learning = LearningAgent()

    def run(self, task):

        task = task.lower()

        if "research" in task:
            return self.research.run(task)

        elif "build" in task:
            return self.builder.run(task)

        elif "career" in task:
            return self.career.run(task)

        elif "learn" in task:
            return self.learning.run(task)

        else:
            return "Task not recognized."