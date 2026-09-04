"""claim-audit: claim-level auditing of reward-hacking transcripts.

Stages run in order 01 to 06. Each stage reads the previous stage's output from
`results/<run_id>/` and writes its own. `schema.py` is the contract between them.
"""

__version__ = "0.1.0"
