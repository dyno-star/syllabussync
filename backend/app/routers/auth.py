from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.db_models import User
from app.models.schemas import UserCreate, UserLogin, UserOut, Token
from app.services.auth import hash_password, verify_password, create_access_token, decode_access_token

router = APIRouter()


@router.post("/register", response_model=Token, status_code=201)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        # Deliberately vague ("already registered" not "email taken by
        # someone else") to avoid confirming account existence to an
        # attacker probing emails — minor hardening, cheap to include.
        raise HTTPException(status_code=400, detail="That email is already registered")

    user = User(email=user_in.email, password_hash=hash_password(user_in.password))
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(str(user.id))
    return Token(access_token=token)


@router.post("/login", response_model=Token)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == credentials.email.lower().strip()).first()

    # Same error message whether the email doesn't exist or the password is
    # wrong — again, avoid confirming which emails have accounts.
    invalid_credentials = HTTPException(status_code=401, detail="Incorrect email or password")

    if not user:
        raise invalid_credentials
    if not verify_password(credentials.password, user.password_hash):
        raise invalid_credentials

    token = create_access_token(str(user.id))
    return Token(access_token=token)


def get_current_user(
    authorization: str = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    """
    FastAPI dependency: every protected route takes
    `current_user: User = Depends(get_current_user)` and gets a real,
    loaded User row — or this raises 401 before the route body ever runs.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = authorization.removeprefix("Bearer ").strip()
    user_id = decode_access_token(token)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    try:
        user_uuid = UUID(user_id)
    except ValueError:
        # A structurally-valid JWT whose "sub" claim isn't a real UUID —
        # shouldn't happen from our own create_access_token, but a
        # malformed/forged token could produce this, and it must fail
        # closed (401) rather than crash the query with a 500.
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.id == user_uuid).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User no longer exists")

    return user


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user
