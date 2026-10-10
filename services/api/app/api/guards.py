"""Small checks shared by routers."""
from __future__ import annotations

import uuid

from fastapi import HTTPException

# Mr Tan is the loaded demo patient (about 90 days of history). Screens that rewrite a person's own profile must not run against his record:
# replaying onboarding or editing the contact while he is selected would overwrite data the demo depends on.
MR_TAN = uuid.UUID("dc48e209-5731-5b3d-89d9-986242c54368")


def not_the_demo_patient(user: object) -> None:
    if str(user) == str(MR_TAN):
        raise HTTPException(409, "Mr Tan is demo data, so his profile cannot be changed here. Switch to the demo user to try this.")
