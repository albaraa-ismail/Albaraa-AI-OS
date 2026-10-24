from agents.chief_agent import ChiefAgent

chief = ChiefAgent()

task = input("Enter Task: ")

result = chief.run(task)

print(result)