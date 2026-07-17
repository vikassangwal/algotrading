import logging
logging.basicConfig(level=logging.DEBUG)
from app.elco_brain import ElcoMasterBrain
brain = ElcoMasterBrain()
result = brain.execute_institutional_workflow("RELIANCE", 2950.0, "Energy", "Value")
print(result)
