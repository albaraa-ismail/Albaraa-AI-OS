class ProjectManagerAgent:

    def run(self, task):
        return f"Project plan created: {task}"

    def create_plan(self, project_name):

        plan = f"""
Project: {project_name}

Phase 1:
- Requirements Analysis
- Research

Phase 2:
- System Design
- Architecture Planning

Phase 3:
- Development
- Testing

Phase 4:
- Documentation
- Deployment

Phase 5:
- Maintenance
- Future Improvements
"""

        return plan