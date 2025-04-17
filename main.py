from fastapi import FastAPI, Request, Form, HTTPException, Response, status, Depends, Query
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, String, inspect, DateTime, Integer, ForeignKey, Text, UniqueConstraint, Float
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
import os
from dotenv import load_dotenv
from passlib.context import CryptContext
import logging
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from starlette.middleware.sessions import SessionMiddleware
from datetime import datetime
import json
from functools import wraps


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get environment variables
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_NAME = os.getenv('DB_NAME', 'user_db')
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')

# Create FastAPI app with proper event loop handling
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add session middleware
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# Mount static directory
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

# Add custom Jinja2 filters
def parse_json(value):
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return []

templates.env.filters["from_json"] = parse_json

# Password hashing setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Database configuration
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"

try:
    engine = create_engine(DATABASE_URL)
    # Test the connection
    with engine.connect() as connection:
        connection.execute("SELECT 1")
    logger.info("Successfully connected to the database")
except Exception as e:
    logger.error(f"Failed to connect to the database: {e}")
    # Create a SQLite database as fallback
    DATABASE_URL = "sqlite:///./local.db"
    engine = create_engine(DATABASE_URL)
    logger.info("Using SQLite as fallback database")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create declarative base
Base = declarative_base()

# User model
class User(Base):
    __tablename__ = "users"

    email = Column(String(120), primary_key=True, index=True)
    password_hash = Column(String(128))
    last_login = Column(DateTime, nullable=True)
    previous_login = Column(DateTime, nullable=True)
    activities = relationship("ActivityLog", back_populates="user")
    game_history = relationship("GameHistory", back_populates="user")
    game_stats = relationship("UserGameStats", back_populates="user")

    def verify_password(self, password):
        return pwd_context.verify(password, self.password_hash)

class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String(120), ForeignKey("users.email"))
    activity_type = Column(String(50))  # login, profile_update, security_alert, etc.
    description = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    device_info = Column(String(255), nullable=True)
    
    user = relationship("User", back_populates="activities")

class GameHistory(Base):
    __tablename__ = "game_history"

    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String(120), ForeignKey("users.email"))
    game_type = Column(String(50))  # e.g., "tictactoe"
    result = Column(String(50))  # e.g., "win", "loss", "draw"
    moves = Column(Text)  # Store game moves as JSON string
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="game_history")

class UserGameStats(Base):
    __tablename__ = "user_game_stats"
    
    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String(120), ForeignKey("users.email"))
    game_type = Column(String(50))  # e.g., "tictactoe", "circle_game"
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    draws = Column(Integer, default=0)
    high_score = Column(Integer, default=0)  # Store high score
    best_time = Column(Float, default=0)  # Store best time in seconds
    
    # Make the combination of user_email and game_type unique
    __table_args__ = (
        UniqueConstraint('user_email', 'game_type', name='uq_user_game_stats'),
    )
    
    user = relationship("User", back_populates="game_stats")

# Initialize database
def init_db():
    try:
        inspector = inspect(engine)
        tables_to_check = ["users", "activity_logs", "game_history", "user_game_stats"]
        tables_exist = all(inspector.has_table(table) for table in tables_to_check)
        
        if not tables_exist:
            Base.metadata.create_all(bind=engine)
            logger.info("Database tables created successfully")
        else:
            logger.info("Database tables already exist")
    except Exception as e:
        logger.error(f"Error checking/creating database tables: {e}")
        raise

# Initialize database
init_db()

def get_current_user(request: Request):
    user_email = request.session.get("user_email")
    if not user_email:
        return None
    return user_email

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return RedirectResponse(url="/login")

@app.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, success: str = None):
    return templates.TemplateResponse("login.html", {"request": request, "success": success})

@app.post("/login")
async def login(request: Request, email: str = Form(...), password: str = Form(...)):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user and user.verify_password(password):
            # Store previous login time before updating
            user.previous_login = user.last_login
            # Update last login time
            user.last_login = datetime.utcnow()
            
            # Log the activity
            activity = ActivityLog(
                user_email=email,
                activity_type="login",
                description="Logged in from your usual device",
                device_info=request.headers.get("user-agent", "Unknown device")
            )
            db.add(activity)
            db.commit()
            
            # Set session
            request.session["user_email"] = user.email
            return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid email or password"}
        )
    finally:
        db.close()

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, current_user: str = Depends(get_current_user)):
    if not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == current_user).first()
        if not user:
            request.session.clear()
            return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
        
        # Fetch recent activities for this user
        recent_activities = db.query(ActivityLog).filter(
            ActivityLog.user_email == current_user
        ).order_by(ActivityLog.timestamp.desc()).limit(10).all()
        
        # Fetch game statistics
        tictactoe_stats = db.query(UserGameStats).filter(
            UserGameStats.user_email == current_user,
            UserGameStats.game_type == "tictactoe"
        ).first()
        
        circle_game_stats = db.query(UserGameStats).filter(
            UserGameStats.user_email == current_user,
            UserGameStats.game_type == "circle_game"
        ).first()
        
        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "user_email": current_user,
                "recent_activities": recent_activities,
                "tictactoe_stats": tictactoe_stats,
                "circle_game_stats": circle_game_stats
            }
        )
    except Exception as e:
        logger.error(f"Error in dashboard: {e}")
        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "user_email": current_user,
                "error": "Error loading dashboard data"
            }
        )
    finally:
        db.close()

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/register")
async def register(request: Request, email: str = Form(...), password: str = Form(...)):
    db = SessionLocal()
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            return templates.TemplateResponse(
                "signup.html",
                {"request": request, "error": "Email already registered"}
            )
            
        # Hash the password and create new user
        password_hash = pwd_context.hash(password)
        user = User(email=email, password_hash=password_hash)
        db.add(user)
        
        # Log the registration activity
        activity = ActivityLog(
            user_email=email,
            activity_type="registration",
            description="Account created",
            device_info=request.headers.get("user-agent", "Unknown device")
        )
        db.add(activity)
        db.commit()
        
        # Redirect to login page with success message
        return RedirectResponse(
            url=f"/login?success=Registration successful! Please login.",
            status_code=status.HTTP_303_SEE_OTHER
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Error during registration: {e}")
        return templates.TemplateResponse(
            "signup.html",
            {"request": request, "error": str(e)}
        )
    finally:
        db.close()

@app.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request):
    return templates.TemplateResponse("forgot_password.html", {"request": request})

@app.post("/reset-password")
async def reset_password(
    request: Request,
    email: str = Form(...),
    old_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...)
):
    db = SessionLocal()
    try:
        # Check if passwords match
        if new_password != confirm_password:
            return templates.TemplateResponse(
                "forgot_password.html",
                {"request": request, "error": "New passwords do not match"}
            )

        # Find user
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return templates.TemplateResponse(
                "forgot_password.html",
                {"request": request, "error": "Email not found"}
            )

        # Verify old password
        if not user.verify_password(old_password):
            return templates.TemplateResponse(
                "forgot_password.html",
                {"request": request, "error": "Current password is incorrect"}
            )

        # Update password
        user.password_hash = pwd_context.hash(new_password)
        db.commit()

        return RedirectResponse(
            url="/login?success=Password updated successfully. Please login with your new password.",
            status_code=status.HTTP_303_SEE_OTHER
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Error during password reset: {e}")
        return templates.TemplateResponse(
            "forgot_password.html",
            {"request": request, "error": "An error occurred. Please try again."}
        )
    finally:
        db.close()

@app.get("/game")
async def game_page(request: Request):
    user_email = request.session.get("user_email")
    if not user_email:
        return RedirectResponse(url="/login")
    
    return templates.TemplateResponse("tictactoe.html", {
        "request": request,
        "user_email": user_email
    })

def login_required(func):
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        if not request.session.get("user_email"):
            return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
        return await func(request, *args, **kwargs)
    return wrapper

@login_required
@app.get("/circle-game", response_class=HTMLResponse)
async def circle_game_page(request: Request, current_user: str = Depends(get_current_user)):
    return templates.TemplateResponse("circle_game.html", {"request": request, "user_email": current_user})

def save_game_history(user_email: str, game_type: str, result: str, moves: str):
    db = SessionLocal()
    try:
        game_history = GameHistory(
            user_email=user_email,
            game_type=game_type,
            result=result,
            moves=moves
        )
        db.add(game_history)
        db.commit()
        logger.info(f"Game history saved for user {user_email}")
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving game history: {e}")
        raise
    finally:
        db.close()

@app.post("/save-game-result")
async def save_game_result(
    request: Request,
    game_type: str = Form(...),
    result: str = Form(...),
    moves: str = Form(...),
    time_taken: float = Form(None),  # New parameter for time taken
    current_user: str = Depends(get_current_user)
):
    if not current_user:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"message": "Not authenticated"}
        )
    
    db = SessionLocal()
    try:
        # Save game history
        save_game_history(current_user, game_type, result, moves)
        
        # Update user game stats
        user_stats = db.query(UserGameStats).filter(
            UserGameStats.user_email == current_user,
            UserGameStats.game_type == game_type
        ).first()
        
        if not user_stats:
            # Create new stats record if it doesn't exist
            user_stats = UserGameStats(
                user_email=current_user,
                game_type=game_type,
                wins=0,
                losses=0,
                draws=0,
                high_score=0,
                best_time=0
            )
            db.add(user_stats)
        
        # Update stats based on game result
        if result == "player" or result == "win":
            user_stats.wins += 1
        elif result == "ai" or result == "loss":
            user_stats.losses += 1
        elif result == "draw":
            user_stats.draws += 1
            
        # Update high score for circle game
        if game_type == "circle_game":
            score = int(moves)  # Convert moves to score for circle game
            if score > user_stats.high_score:
                user_stats.high_score = score
            
            # Update best time if provided and better than current
            if time_taken and (user_stats.best_time == 0 or time_taken < user_stats.best_time):
                user_stats.best_time = time_taken
        
        # Log activity based on game result
        activity_type = "game_played"
        description = f"Played a game of {game_type}"
        
        if result == "win" or result == "player":
            activity_type = "game_win"
            description = f"Won a game of {game_type}"
        elif result == "loss" or result == "ai":
            activity_type = "game_loss"
            description = f"Lost a game of {game_type}"
        elif result == "draw":
            activity_type = "game_draw"
            description = f"Tied a game of {game_type}"
        
        # Create activity log entry
        activity = ActivityLog(
            user_email=current_user,
            activity_type=activity_type,
            description=description,
            device_info=request.headers.get("user-agent", "Unknown device")
        )
        db.add(activity)
        db.commit()
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Game result saved successfully"}
        )
    except Exception as e:
        db.rollback()
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": f"Error saving game result: {str(e)}"}
        )
    finally:
        db.close()

@app.get("/game-history")
async def get_game_history(
    request: Request,
    current_user: str = Depends(get_current_user)
):
    if not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    
    db = SessionLocal()
    try:
        # Get game history with user relationship
        game_history = db.query(GameHistory).filter(
            GameHistory.user_email == current_user
        ).order_by(GameHistory.timestamp.desc()).all()
        
        # Process the game moves for tictactoe games
        for game in game_history:
            if game.game_type == 'tictactoe' and game.moves:
                try:
                    # Try to parse the JSON if it's in JSON format
                    game.parsed_moves = json.loads(game.moves)
                except (json.JSONDecodeError, TypeError):
                    # If not in JSON format, handle plain string
                    if isinstance(game.moves, str) and '[' in game.moves and ']' in game.moves:
                        # Handle Python-like list string
                        cleaned = game.moves.replace('[', '').replace(']', '').replace('\'', '').replace('"', '')
                        game.parsed_moves = [item.strip() for item in cleaned.split(',')]
                    else:
                        game.parsed_moves = []
            else:
                game.parsed_moves = []
        
        if not game_history:
            return templates.TemplateResponse(
                "game_history.html",
                {
                    "request": request,
                    "user_email": current_user,
                    "game_history": [],
                    "message": "No game history found."
                }
            )
        
        return templates.TemplateResponse(
            "game_history.html",
            {
                "request": request,
                "user_email": current_user,
                "game_history": game_history,
                "message": None
            }
        )
    except Exception as e:
        logger.error(f"Error fetching game history: {e}")
        return templates.TemplateResponse(
            "game_history.html",
            {
                "request": request,
                "user_email": current_user,
                "game_history": [],
                "message": f"Error loading game history: {str(e)}"
            }
        )
    finally:
        db.close()

@app.get("/api/game-scores", response_class=JSONResponse)
async def get_game_scores(
    request: Request,
    game_type: str = Query(default="tictactoe", description="Type of game to get scores for"),
    current_user: str = Depends(get_current_user)
):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    db = SessionLocal()
    try:
        # Get or create user game stats
        user_stats = db.query(UserGameStats).filter(
            UserGameStats.user_email == current_user,
            UserGameStats.game_type == game_type
        ).first()
        
        if not user_stats:
            return JSONResponse(
                content={
                    "wins": 0,
                    "losses": 0,
                    "draws": 0,
                    "high_score": 0,
                    "best_time": 0
                }
            )
        
        return JSONResponse(
            content={
                "wins": user_stats.wins,
                "losses": user_stats.losses,
                "draws": user_stats.draws,
                "high_score": user_stats.high_score,
                "best_time": user_stats.best_time
            }
        )
    except Exception as e:
        logger.error(f"Error fetching game scores: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching game scores: {str(e)}"
        )
    finally:
        db.close()

@app.post("/api/reset-game-scores", response_class=JSONResponse)
async def reset_game_scores(
    request: Request,
    game_type: str = Form(...),
    current_user: str = Depends(get_current_user)
):
    if not current_user:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"message": "Not authenticated"}
        )
    
    db = SessionLocal()
    try:
        # Find user stats
        user_stats = db.query(UserGameStats).filter(
            UserGameStats.user_email == current_user,
            UserGameStats.game_type == game_type
        ).first()
        
        if user_stats:
            # Reset the stats to zero
            user_stats.wins = 0
            user_stats.losses = 0
            user_stats.draws = 0
            db.commit()
            
            # Log the activity
            activity = ActivityLog(
                user_email=current_user,
                activity_type="game_stats_reset",
                description=f"Reset {game_type} game statistics",
                device_info=request.headers.get("user-agent", "Unknown device")
            )
            db.add(activity)
            db.commit()
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Game scores reset successfully",
                "player": 0,
                "ai": 0,
                "draws": 0
            }
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Error resetting game scores: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": f"Error resetting game scores: {str(e)}"}
        )
    finally:
        db.close()

@app.get("/memory-game", response_class=HTMLResponse)
async def memory_game(request: Request, current_user: str = Depends(get_current_user)):
    if not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse("memory_game.html", {
        "request": request,
        "user_email": current_user
    })

@app.get("/word-guess", response_class=HTMLResponse)
@login_required
async def word_guess(request: Request, current_user: str = Depends(get_current_user)):
    if not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse("word_guess.html", {
        "request": request,
        "user_email": current_user
    })

@app.get("/math-challenge", response_class=HTMLResponse)
@login_required
async def math_challenge(request: Request, current_user: str = Depends(get_current_user)):
    if not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse("math_challenge.html", {
        "request": request,
        "user_email": current_user
    })

@app.get("/rps-game", response_class=HTMLResponse)
@login_required
async def rps_game(request: Request, current_user: str = Depends(get_current_user)):
    if not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse("rps_game.html", {
        "request": request,
        "user_email": current_user
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 