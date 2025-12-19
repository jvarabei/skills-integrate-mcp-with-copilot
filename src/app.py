"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os
from pathlib import Path
from typing import Optional

from sqlmodel import SQLModel, Field, Relationship, Session, create_engine, select

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data.db")
engine = create_engine(DATABASE_URL, echo=False)


class Participant(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str
    activity_name: str = Field(foreign_key="activity.name")
    activity: Optional["Activity"] = Relationship(back_populates="participants")


class Activity(SQLModel, table=True):
    name: str = Field(primary_key=True)
    description: str
    schedule: str
    max_participants: int

    participants: list[Participant] = Relationship(back_populates="activity")


def init_db_with_seed() -> None:
    SQLModel.metadata.create_all(engine)

    # Seed only if empty
    with Session(engine) as session:
        first = session.exec(select(Activity)).first()
        if first:
            return

        seed = {
            "Chess Club": {
                "description": "Learn strategies and compete in chess tournaments",
                "schedule": "Fridays, 3:30 PM - 5:00 PM",
                "max_participants": 12,
                "participants": ["michael@mergington.edu", "daniel@mergington.edu"],
            },
            "Programming Class": {
                "description": "Learn programming fundamentals and build software projects",
                "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
                "max_participants": 20,
                "participants": ["emma@mergington.edu", "sophia@mergington.edu"],
            },
            "Gym Class": {
                "description": "Physical education and sports activities",
                "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
                "max_participants": 30,
                "participants": ["john@mergington.edu", "olivia@mergington.edu"],
            },
            "Soccer Team": {
                "description": "Join the school soccer team and compete in matches",
                "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
                "max_participants": 22,
                "participants": ["liam@mergington.edu", "noah@mergington.edu"],
            },
            "Basketball Team": {
                "description": "Practice and play basketball with the school team",
                "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
                "max_participants": 15,
                "participants": ["ava@mergington.edu", "mia@mergington.edu"],
            },
            "Art Club": {
                "description": "Explore your creativity through painting and drawing",
                "schedule": "Thursdays, 3:30 PM - 5:00 PM",
                "max_participants": 15,
                "participants": ["amelia@mergington.edu", "harper@mergington.edu"],
            },
            "Drama Club": {
                "description": "Act, direct, and produce plays and performances",
                "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
                "max_participants": 20,
                "participants": ["ella@mergington.edu", "scarlett@mergington.edu"],
            },
            "Math Club": {
                "description": "Solve challenging problems and participate in math competitions",
                "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
                "max_participants": 10,
                "participants": ["james@mergington.edu", "benjamin@mergington.edu"],
            },
            "Debate Team": {
                "description": "Develop public speaking and argumentation skills",
                "schedule": "Fridays, 4:00 PM - 5:30 PM",
                "max_participants": 12,
                "participants": ["charlotte@mergington.edu", "henry@mergington.edu"],
            },
        }

        for name, data in seed.items():
            a = Activity(
                name=name,
                description=data["description"],
                schedule=data["schedule"],
                max_participants=data["max_participants"],
            )
            session.add(a)
            for email in data["participants"]:
                session.add(Participant(email=email, activity_name=name))
        session.commit()


def activities_as_dict() -> dict:
    """Return activities in the same structure as the original in-memory API."""
    with Session(engine) as session:
        result = {}
        activities = session.exec(select(Activity)).all()
        for a in activities:
            # Load participants for this activity
            emails = [p.email for p in a.participants]
            result[a.name] = {
                "description": a.description,
                "schedule": a.schedule,
                "max_participants": a.max_participants,
                "participants": emails,
            }
        return result


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return activities_as_dict()


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str):
    """Sign up a student for an activity"""
    with Session(engine) as session:
        activity = session.get(Activity, activity_name)
        if not activity:
            raise HTTPException(status_code=404, detail="Activity not found")

        # Check if already signed up
        existing = session.exec(
            select(Participant).where(
                (Participant.activity_name == activity_name) & (Participant.email == email)
            )
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Student is already signed up")

        # Add student
        session.add(Participant(email=email, activity_name=activity_name))
        session.commit()
        return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str):
    """Unregister a student from an activity"""
    with Session(engine) as session:
        activity = session.get(Activity, activity_name)
        if not activity:
            raise HTTPException(status_code=404, detail="Activity not found")

        participant = session.exec(
            select(Participant).where(
                (Participant.activity_name == activity_name) & (Participant.email == email)
            )
        ).first()
        if not participant:
            raise HTTPException(status_code=400, detail="Student is not signed up for this activity")

        session.delete(participant)
        session.commit()
        return {"message": f"Unregistered {email} from {activity_name}"}


@app.on_event("startup")
def on_startup() -> None:
    init_db_with_seed()
