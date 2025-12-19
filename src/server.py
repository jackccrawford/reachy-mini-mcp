"""
Reachy Mini MCP Server
======================
MCP tools for controlling Pollen Robotics Reachy Mini robot.

Architecture:
  MCP Tool Call → SDK → Robot Movement

High-level tools abstract motor control into semantic actions.

Tools:
  - express(emotion)      High-level emotional expression (12 built-in)
  - play_move(name)       Pollen's recorded moves (40+ emotions, dances)
  - list_moves()          Discover available recorded moves
  - look_at(angles)       Direct head positioning
  - antenna(angles)       Antenna control
  - rotate(direction)     Body rotation
  - speak(text/file)      Audio output (TTS via Deepgram)
  - listen(duration)      Audio capture
  - see()                 Camera capture
  - rest()                Return to neutral pose
"""

import math
import base64
from typing import Optional, Literal

import numpy as np
from fastmcp import FastMCP

# Initialize MCP server
mcp = FastMCP(
    name="reachy-mini",
    instructions="""
    Reachy Mini robot control for expressive robotics.

    Use these tools for robot control:
    - express() for 12 built-in emotions (curious, joy, thinking, etc.)
    - play_move() for 40+ recorded emotions from Pollen (fear1, rage1, serenity1, etc.)
    - list_moves() to discover available recorded moves
    - look_at() for precise head positioning
    - speak() to vocalize
    - see() to capture camera images

    Prefer express() for common emotions, play_move() for nuanced expressions.
    """
)

# ==============================================================================
# EXPRESSION MAPPINGS
# ==============================================================================
# High-level emotions → motor choreography
# Head pose: (x, y, z, roll, pitch, yaw) - z is height, roll/pitch/yaw are degrees
# Antennas: [left, right] in degrees

EXPRESSIONS = {
    "neutral": {
        "head": {"z": 0, "roll": 0, "pitch": 0, "yaw": 0},
        "antennas": [0, 0],
        "duration": 1.5,
        "method": "minjerk"
    },
    "curious": {
        "head": {"z": 0, "roll": 0, "pitch": 10, "yaw": 8},  # Forward, slight turn
        "antennas": [20, 20],  # Both up, alert
        "duration": 1.2,
        "method": "ease_in_out"
    },
    "uncertain": {
        "head": {"z": 0, "roll": 8, "pitch": -3, "yaw": 3},  # Head tilt, slight back
        "antennas": [-15, 15],  # Asymmetric - confusion
        "duration": 2.0,
        "method": "minjerk"
    },
    "recognition": {
        "head": {"z": 0, "roll": 0, "pitch": 5, "yaw": 0},  # Slight forward - attention
        "antennas": [30, 30],  # Both high - alert/happy
        "duration": 0.8,
        "method": "cartoon"
    },
    "joy": {
        "head": {"z": 0, "roll": -3, "pitch": 8, "yaw": 0},  # Head up and forward
        "antennas": [40, 40],  # Elevated
        "duration": 1.0,
        "method": "cartoon"
    },
    "thinking": {
        "head": {"z": 0, "roll": 5, "pitch": 3, "yaw": 12},  # Tilt, look away slightly
        "antennas": [8, -8],  # Slight asymmetry
        "duration": 1.5,
        "method": "ease_in_out"
    },
    "listening": {
        "head": {"z": 0, "roll": -3, "pitch": 8, "yaw": 0},  # Attentive forward lean
        "antennas": [25, 25],  # Alert
        "duration": 1.0,
        "method": "minjerk"
    },
    "agreeing": {
        "head": {"z": 0, "roll": 0, "pitch": 8, "yaw": 0},  # Nod forward
        "antennas": [20, 20],
        "duration": 0.5,
        "method": "ease_in_out"
    },
    "disagreeing": {
        "head": {"z": 0, "roll": 0, "pitch": 0, "yaw": 12},  # Shake start
        "antennas": [-8, -8],  # Slightly down
        "duration": 0.4,
        "method": "ease_in_out"
    },
    "sleepy": {
        "head": {"z": 0, "roll": 8, "pitch": -10, "yaw": 0},  # Head droops
        "antennas": [-20, -20],  # Down
        "duration": 2.5,
        "method": "minjerk"
    },
    "surprised": {
        "head": {"z": 0, "roll": 0, "pitch": -8, "yaw": 0},  # Pull back
        "antennas": [45, 45],  # High alert
        "duration": 0.3,
        "method": "cartoon"
    },
    "focused": {
        "head": {"z": 0, "roll": 0, "pitch": 6, "yaw": 0},  # Forward, intent
        "antennas": [18, 18],  # Alert but not excited
        "duration": 1.0,
        "method": "minjerk"
    }
}


# ==============================================================================
# CONNECTION MANAGEMENT
# ==============================================================================

_robot_instance = None

def get_robot():
    """
    Get or create robot connection.
    Uses lazy initialization - connects on first tool call.
    Uses no_media backend for headless simulation compatibility.
    """
    global _robot_instance
    if _robot_instance is None:
        try:
            from reachy_mini import ReachyMini
            # Use default_no_video for simulation (keeps audio, skips camera)
            # Use 'no_media' for fully headless, 'default' for real hardware
            _robot_instance = ReachyMini(media_backend='default_no_video')
            _robot_instance.__enter__()
        except ImportError:
            raise RuntimeError(
                "reachy-mini SDK not installed. Run: pip install reachy-mini[mujoco]"
            )
        except Exception as e:
            raise RuntimeError(
                f"Could not connect to Reachy Mini. Is the daemon running? Error: {e}"
            )
    return _robot_instance


def cleanup_robot():
    """Clean up robot connection on shutdown."""
    global _robot_instance
    if _robot_instance is not None:
        try:
            _robot_instance.__exit__(None, None, None)
        except:
            pass
        _robot_instance = None


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def degrees_to_radians(degrees: float) -> float:
    """Convert degrees to radians for SDK calls."""
    return degrees * (math.pi / 180.0)


def create_head_pose_array(z: float = 0, roll: float = 0, pitch: float = 0, yaw: float = 0):
    """
    Create head pose transformation matrix.

    Args:
        z: Vertical position offset
        roll: Tilt left/right in degrees (positive = right ear toward shoulder)
        pitch: Nod up/down in degrees (positive = looking up)
        yaw: Turn left/right in degrees (positive = looking right)

    Returns:
        4x4 numpy transformation matrix
    """
    from reachy_mini.utils import create_head_pose
    return create_head_pose(z=z, roll=roll, pitch=pitch, yaw=yaw, degrees=True)


def get_interpolation_method(method: str):
    """Get interpolation enum from string."""
    from reachy_mini.utils.interpolation import InterpolationTechnique

    methods = {
        "linear": InterpolationTechnique.LINEAR,
        "minjerk": InterpolationTechnique.MIN_JERK,
        "ease_in_out": InterpolationTechnique.EASE_IN_OUT,
        "cartoon": InterpolationTechnique.CARTOON,
    }
    return methods.get(method, InterpolationTechnique.MIN_JERK)


# ==============================================================================
# MCP TOOLS
# ==============================================================================

@mcp.tool()
def express(
    emotion: Literal[
        "neutral", "curious", "uncertain", "recognition", "joy",
        "thinking", "listening", "agreeing", "disagreeing",
        "sleepy", "surprised", "focused"
    ]
) -> str:
    """
    Express an emotion through physical movement.

    High-level tool that maps emotions to motor choreography.
    Caller specifies WHAT to express; tool handles HOW to move.

    Available emotions:
    - neutral: Rest position, attentive
    - curious: Forward lean, alert antennas - "what's that?"
    - uncertain: Head tilt, asymmetric antennas - "I'm not sure"
    - recognition: Quick attention, high antennas - "I see you"
    - joy: Head up, maximum antenna elevation - happiness
    - thinking: Look away slightly, processing
    - listening: Attentive lean, focused on input
    - agreeing: Nodding motion
    - disagreeing: Shake motion
    - sleepy: Drooping, low energy
    - surprised: Pull back, maximum alert
    - focused: Intent forward gaze

    Args:
        emotion: The emotional state to express

    Returns:
        Confirmation of expression executed
    """
    if emotion not in EXPRESSIONS:
        return f"Unknown emotion: {emotion}. Available: {list(EXPRESSIONS.keys())}"

    expr = EXPRESSIONS[emotion]
    robot = get_robot()

    try:
        head = expr["head"]
        antennas = expr["antennas"]

        # Convert antenna degrees to radians
        antenna_radians = [degrees_to_radians(a) for a in antennas]

        robot.goto_target(
            head=create_head_pose_array(
                z=head["z"],
                roll=head["roll"],
                pitch=head["pitch"],
                yaw=head["yaw"]
            ),
            antennas=antenna_radians,
            duration=expr["duration"],
            method=get_interpolation_method(expr["method"])
        )

        return f"Expressed: {emotion}"

    except Exception as e:
        return f"Expression failed: {e}"


@mcp.tool()
def look_at(
    roll: float = 0,
    pitch: float = 0,
    yaw: float = 0,
    z: float = 0,
    duration: float = 1.0
) -> str:
    """
    Direct head positioning in degrees.

    Use this for precise control when express() doesn't fit.
    For most cases, prefer express() for cognitive simplicity.

    Args:
        roll: Tilt left/right (-45 to 45). Positive = right ear to shoulder
        pitch: Nod up/down (-30 to 30). Positive = looking up
        yaw: Turn left/right (-90 to 90). Positive = looking right
        z: Vertical offset (-20 to 20). Positive = head higher
        duration: Movement time in seconds (0.1 to 5.0)

    Returns:
        Confirmation of movement
    """
    # Clamp values to safe ranges
    roll = max(-45, min(45, roll))
    pitch = max(-30, min(30, pitch))
    yaw = max(-90, min(90, yaw))
    z = max(-20, min(20, z))
    duration = max(0.1, min(5.0, duration))

    robot = get_robot()

    try:
        robot.goto_target(
            head=create_head_pose_array(z=z, roll=roll, pitch=pitch, yaw=yaw),
            duration=duration,
            method=get_interpolation_method("minjerk")
        )
        return f"Head positioned: roll={roll}°, pitch={pitch}°, yaw={yaw}°, z={z}"

    except Exception as e:
        return f"Movement failed: {e}"


@mcp.tool()
def antenna(
    left: float = 0,
    right: float = 0,
    duration: float = 0.5
) -> str:
    """
    Control antenna positions for expression.

    Antennas are highly expressive - use for emotional signaling.
    Symmetric = stable emotion. Asymmetric = uncertainty/confusion.

    Args:
        left: Left antenna angle (-45 to 90). Positive = up
        right: Right antenna angle (-45 to 90). Positive = up
        duration: Movement time in seconds

    Returns:
        Confirmation
    """
    left = max(-45, min(90, left))
    right = max(-45, min(90, right))
    duration = max(0.1, min(3.0, duration))

    robot = get_robot()

    try:
        robot.goto_target(
            antennas=[degrees_to_radians(left), degrees_to_radians(right)],
            duration=duration,
            method=get_interpolation_method("ease_in_out")
        )
        return f"Antennas: left={left}°, right={right}°"

    except Exception as e:
        return f"Antenna movement failed: {e}"


@mcp.tool()
def rotate(
    direction: Literal["left", "right", "center"],
    degrees: float = 45
) -> str:
    """
    Rotate body toward a direction.

    Use to orient toward or away from something.

    Args:
        direction: Which way to turn
        degrees: How far to turn (10-180)

    Returns:
        Confirmation
    """
    degrees = max(10, min(180, abs(degrees)))

    if direction == "left":
        yaw = -degrees_to_radians(degrees)
    elif direction == "right":
        yaw = degrees_to_radians(degrees)
    else:  # center
        yaw = 0

    robot = get_robot()

    try:
        robot.goto_target(
            body_yaw=yaw,
            duration=1.5,
            method=get_interpolation_method("minjerk")
        )
        return f"Rotated {direction}" + (f" {degrees}°" if direction != "center" else "")

    except Exception as e:
        return f"Rotation failed: {e}"


def text_to_speech(text: str) -> str:
    """
    Convert text to speech using Deepgram TTS.
    Returns path to temporary audio file.
    """
    import tempfile
    import httpx
    import os

    api_key = os.environ.get("DEEPGRAM_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPGRAM_API_KEY environment variable not set")

    url = "https://api.deepgram.com/v1/speak?model=aura-2-saturn-en"
    headers = {
        "Authorization": f"Token {api_key}",
        "Content-Type": "application/json"
    }
    data = {"text": text}

    response = httpx.post(url, headers=headers, json=data, timeout=30.0)
    response.raise_for_status()

    # Save to temp file
    temp_file = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    temp_file.write(response.content)
    temp_file.close()

    return temp_file.name


@mcp.tool()
def speak(text: str) -> str:
    """
    Speak through the robot's speaker.

    Uses text-to-speech to vocalize. For pre-recorded audio,
    provide a file path instead of text.

    Args:
        text: What to say (or path to audio file)

    Returns:
        Confirmation
    """
    robot = get_robot()

    try:
        # Check if it's a file path
        if text.endswith(('.wav', '.mp3', '.ogg')):
            robot.media.play_sound(text)
            return f"Played audio: {text}"
        else:
            # Convert text to speech via Deepgram
            audio_path = text_to_speech(text)
            robot.media.play_sound(audio_path)

            # Clean up temp file
            import os
            os.unlink(audio_path)

            return f"Spoke: {text}"

    except Exception as e:
        return f"Speech failed: {e}"


@mcp.tool()
def listen(duration: float = 3.0) -> str:
    """
    Listen through the robot's microphones.

    Captures audio for the specified duration.
    Returns base64-encoded audio data.

    Args:
        duration: How long to listen in seconds (1-30)

    Returns:
        Base64-encoded audio sample
    """
    duration = max(1, min(30, duration))
    robot = get_robot()

    try:
        audio_data = robot.media.get_audio_sample(duration=duration)

        if audio_data is not None:
            encoded = base64.b64encode(audio_data).decode('utf-8')
            return f"Audio captured ({duration}s): {encoded[:100]}..."
        else:
            return "No audio captured"

    except Exception as e:
        return f"Listen failed: {e}"


@mcp.tool()
def see() -> str:
    """
    Capture an image from the robot's camera.

    Returns the current view as base64-encoded image.
    Use this to perceive the environment.

    Returns:
        Base64-encoded image data (JPEG)
    """
    robot = get_robot()

    try:
        frame = robot.media.get_frame()

        if frame is not None:
            import cv2
            _, buffer = cv2.imencode('.jpg', frame)
            encoded = base64.b64encode(buffer).decode('utf-8')
            return f"data:image/jpeg;base64,{encoded}"
        else:
            return "No frame captured"

    except ImportError:
        return "OpenCV not available for image encoding"
    except Exception as e:
        return f"Vision failed: {e}"


@mcp.tool()
def rest() -> str:
    """
    Return to neutral rest position.

    Use when transitioning away or ending interaction.
    Gentle movement to default pose.

    Returns:
        Confirmation
    """
    return express("neutral")


@mcp.tool()
def wake_up() -> str:
    """
    Wake up the robot from sleep mode.

    Call this before any other movements.

    Returns:
        Confirmation
    """
    robot = get_robot()
    try:
        robot.wake_up()
        return "Robot awakened"
    except Exception as e:
        return f"Wake up failed: {e}"


@mcp.tool()
def sleep() -> str:
    """
    Put the robot into sleep mode.

    Use when ending interaction or to save power.

    Returns:
        Confirmation
    """
    robot = get_robot()
    try:
        robot.goto_sleep()
        return "Robot sleeping"
    except Exception as e:
        return f"Sleep failed: {e}"


# ==============================================================================
# RECORDED MOVES (Pollen's emotion/dance libraries)
# ==============================================================================

DAEMON_URL = "http://localhost:8321/api"

MOVE_LIBRARIES = {
    "emotions": "pollen-robotics/reachy-mini-emotions-library",
    "dances": "pollen-robotics/reachy-mini-dances-library",
}


@mcp.tool()
def list_moves(library: Literal["emotions", "dances"] = "emotions") -> str:
    """
    List available recorded moves from Pollen's HuggingFace libraries.

    Returns move names that can be passed to play_move().
    Moves are professionally choreographed by Pollen Robotics.

    Args:
        library: Which library to list - "emotions" (40+ expressions) or "dances"

    Returns:
        List of available move names
    """
    import httpx

    dataset = MOVE_LIBRARIES.get(library)
    if not dataset:
        return f"Unknown library: {library}. Available: {list(MOVE_LIBRARIES.keys())}"

    try:
        response = httpx.get(
            f"{DAEMON_URL}/move/recorded-move-datasets/list/{dataset}",
            timeout=10.0
        )
        response.raise_for_status()
        moves = response.json()
        return f"Available {library} ({len(moves)}): {', '.join(sorted(moves))}"
    except httpx.ConnectError:
        return "Cannot connect to daemon. Is it running on localhost:8321?"
    except Exception as e:
        return f"Failed to list moves: {e}"


@mcp.tool()
def play_move(
    move_name: str,
    library: Literal["emotions", "dances"] = "emotions"
) -> str:
    """
    Play a recorded move from Pollen's libraries.

    Use list_moves() first to see available options.
    These are professionally choreographed expressions with
    nuanced head, antenna, and body movements.

    Examples: fear1, loving1, dance3, rage1, serenity1, proud3

    Args:
        move_name: Name of the move (e.g., "fear1", "dance3")
        library: Which library - "emotions" or "dances"

    Returns:
        Confirmation or error
    """
    import httpx

    dataset = MOVE_LIBRARIES.get(library)
    if not dataset:
        return f"Unknown library: {library}. Available: {list(MOVE_LIBRARIES.keys())}"

    try:
        response = httpx.post(
            f"{DAEMON_URL}/move/play/recorded-move-dataset/{dataset}/{move_name}",
            timeout=30.0
        )
        if response.status_code == 404:
            return f"Move '{move_name}' not found in {library}. Use list_moves() to see available options."
        response.raise_for_status()
        result = response.json()
        return f"Playing: {move_name} (uuid: {result.get('uuid', 'unknown')})"
    except httpx.ConnectError:
        return "Cannot connect to daemon. Is it running on localhost:8321?"
    except Exception as e:
        return f"Failed to play move: {e}"


# ==============================================================================
# COMPOUND EXPRESSIONS (sequences)
# ==============================================================================

@mcp.tool()
def nod(times: int = 2) -> str:
    """
    Nod head in agreement.

    Args:
        times: Number of nods (1-5)

    Returns:
        Confirmation
    """
    times = max(1, min(5, times))
    robot = get_robot()

    try:
        for _ in range(times):
            # Nod down
            robot.goto_target(
                head=create_head_pose_array(pitch=15, z=3),
                duration=0.25,
                method=get_interpolation_method("ease_in_out")
            )
            # Nod up
            robot.goto_target(
                head=create_head_pose_array(pitch=-5, z=-2),
                duration=0.25,
                method=get_interpolation_method("ease_in_out")
            )

        # Return to neutral
        robot.goto_target(
            head=create_head_pose_array(pitch=0, z=0),
            duration=0.3,
            method=get_interpolation_method("minjerk")
        )

        return f"Nodded {times} time(s)"

    except Exception as e:
        return f"Nod failed: {e}"


@mcp.tool()
def shake(times: int = 2) -> str:
    """
    Shake head in disagreement.

    Args:
        times: Number of shakes (1-5)

    Returns:
        Confirmation
    """
    times = max(1, min(5, times))
    robot = get_robot()

    try:
        for _ in range(times):
            # Turn right
            robot.goto_target(
                head=create_head_pose_array(yaw=20),
                duration=0.2,
                method=get_interpolation_method("ease_in_out")
            )
            # Turn left
            robot.goto_target(
                head=create_head_pose_array(yaw=-20),
                duration=0.2,
                method=get_interpolation_method("ease_in_out")
            )

        # Return to center
        robot.goto_target(
            head=create_head_pose_array(yaw=0),
            duration=0.3,
            method=get_interpolation_method("minjerk")
        )

        return f"Shook head {times} time(s)"

    except Exception as e:
        return f"Shake failed: {e}"


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    """Run the MCP server."""
    import atexit
    atexit.register(cleanup_robot)
    mcp.run()


if __name__ == "__main__":
    main()
