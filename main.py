
"""
FastAPI Backend for Clinic Voice Agent
Handles availability checking and appointment booking
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
from typing import List
import json

app = FastAPI(title="Clinic Voice Agent Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

KNOWLEDGE_BASE_FILE = "knowledge_base.json"
SCHEDULES_FILE = "schedules.json"
APPOINTMENTS_FILE = "appointments.json"


def load_json(filename: str) -> dict | list:
    """Load JSON data from file"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail=f"File {filename} not found")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail=f"Invalid JSON in {filename}")


def save_json(filename: str, data: dict | list):
    """Save JSON data to file"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def generate_time_slots(start: str, end: str, interval: int = 30) -> List[str]:
    """Generate time slots between start and end time with given interval in minutes"""
    slots = []
    start_time = datetime.strptime(start, "%H:%M")
    end_time = datetime.strptime(end, "%H:%M")
    
    current_time = start_time
    while current_time < end_time:
        slots.append(current_time.strftime("%H:%M"))
        current_time += timedelta(minutes=interval)
    
    return slots


def get_day_date(day_name: str) -> datetime:
    """Get the next occurrence of the given day name"""
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    today = datetime.now()
    target_day = days.index(day_name.capitalize())
    current_day = today.weekday()
    
    days_ahead = target_day - current_day
    if days_ahead < 0:
        days_ahead += 7
    elif days_ahead == 0:
        days_ahead = 0
    
    return today + timedelta(days=days_ahead)


def _ordinal(n: int) -> str:
    """Return ordinal string for an integer (1 -> 1st, 2 -> 2nd, etc.)"""
    if 10 <= (n % 100) <= 20:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f"{n}{suffix}"


def format_date_ordinal(dt: datetime) -> str:
    """Format a datetime as an ordinal day with short month and year, e.g. '4th Nov 2025'"""
    return f"{_ordinal(dt.day)} {dt.strftime('%b')} {dt.year}"


def is_time_in_range(time_str: str, start: datetime, end: datetime, date_obj: datetime) -> bool:
    """Check if a time slot overlaps with a booked appointment"""
    slot_time = datetime.strptime(time_str, "%H:%M")
    slot_datetime = date_obj.replace(
        hour=slot_time.hour,
        minute=slot_time.minute,
        second=0,
        microsecond=0
    )
    
    slot_end = slot_datetime + timedelta(minutes=30)
    return (slot_datetime < end and slot_end > start)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "service": "Clinic Voice Agent Backend",
        "version": "1.0.0"
    }


@app.get("/ping")
async def ping():
    """Minimal endpoint for cron keep-alive"""
    return {"ok": 1}


@app.get("/today")
async def get_today():
    """Get current day and date"""
    today = datetime.now()
    return {
        "day": today.strftime("%A"),
        "date": today.strftime("%Y-%m-%d"),
        "formatted_date": today.strftime("%B %d, %Y")
    }


@app.delete("/appointments/clear")
async def clear_all_appointments():
    """Clear all appointments (admin only)"""
    save_json(APPOINTMENTS_FILE, [])
    return {"status": "success", "message": "All appointments cleared"}


@app.delete("/appointments/{index}")
async def delete_appointment(index: int):
    """Delete a specific appointment by index"""
    appointments = load_json(APPOINTMENTS_FILE)
    if 0 <= index < len(appointments):
        deleted = appointments.pop(index)
        save_json(APPOINTMENTS_FILE, appointments)
        return {"status": "success", "deleted": deleted}
    else:
        raise HTTPException(status_code=404, detail="Appointment not found")


@app.get("/knowledge_base")
async def get_knowledge_base():
    """Get the complete knowledge base for the voice agent"""
    return load_json(KNOWLEDGE_BASE_FILE)


@app.get("/appointments")
async def get_all_appointments():
    """Get all booked appointments"""
    return load_json(APPOINTMENTS_FILE)


@app.get("/schedules")
async def get_schedules():
    """Get doctor schedules for all days"""
    return load_json(SCHEDULES_FILE)


@app.get("/get_slots/{day}")
async def get_slots(day: str):
    """Get available appointment slots for a specific day"""
    try:
        day = day.capitalize()
        
        schedules = load_json(SCHEDULES_FILE)
        if day not in schedules:
            return {
                "response": f"Sorry, the clinic is closed on {day}. We're open Monday through Saturday."
            }
        
        schedule = schedules[day]
        doctor = schedule["doctor"]
        start_time = schedule["start_time"]
        end_time = schedule["end_time"]
        
        all_slots = generate_time_slots(start_time, end_time, interval=30)
        
        lunch_start = "13:00"
        lunch_end = "14:00"
        available_slots = [
            slot for slot in all_slots
            if not (lunch_start <= slot < lunch_end)
        ]
        
        day_date = get_day_date(day)
        appointments = load_json(APPOINTMENTS_FILE)
        
        for appointment in appointments:
            appt_start = datetime.fromisoformat(appointment["start_time"])
            appt_end = datetime.fromisoformat(appointment["end_time"])
            
            if appt_start.date() == day_date.date():
                available_slots = [
                    slot for slot in available_slots
                    if not is_time_in_range(slot, appt_start, appt_end, day_date)
                ]
        
        if available_slots:
            first_slot = available_slots[0]
            last_slot = available_slots[-1]
            response = f"{doctor} is available on {day} from {first_slot} to {last_slot}. What time would you like to book?"
        else:
            response = f"I'm sorry, {doctor} is fully booked on {day}. Would you like to try another day?"
        
        return {
            "response": response,
            "doctor": doctor,
            "day": day,
            "available_slots": available_slots
        }
    
    except Exception as e:
        print(f"Error in check_availability webhook: {e}")
        return {
            "response": "I'm having trouble checking availability right now. Please try again."
        }


@app.post("/log_booking")
async def log_booking(request: dict):
    """Book an appointment"""
    try:
        name = request.get("name", "").strip()
        doctor = request.get("doctor", "").strip()
        day = request.get("day", "").capitalize()
        slot = request.get("slot", "").strip()
        
        if not all([name, doctor, day, slot]):
            return {
                "response": "I need your name, the doctor, day, and time slot to book the appointment. Let's start over."
            }
        
        schedules = load_json(SCHEDULES_FILE)

        # Day and doctor basic checks
        if day not in schedules:
            return {
                "response": f"Sorry, the clinic is closed on {day}. Please choose a weekday or Saturday."
            }

        if schedules[day]["doctor"] != doctor:
            return {
                "response": f"{doctor} is not available on {day}. {schedules[day]['doctor']} is available that day."
            }

        # Validate slot time format
        try:
            slot_time = datetime.strptime(slot, "%H:%M")
        except ValueError:
            return {"response": f"I couldn't understand the time '{slot}'. Please provide it in 24-hour format like 14:00."}

        day_date = get_day_date(day)
        start_datetime = day_date.replace(
            hour=slot_time.hour,
            minute=slot_time.minute,
            second=0,
            microsecond=0
        )
        end_datetime = start_datetime + timedelta(minutes=30)

        # Check working hours and lunch break
        work_start = datetime.strptime(schedules[day]["start_time"], "%H:%M").time()
        work_end = datetime.strptime(schedules[day]["end_time"], "%H:%M").time()
        slot_time_only = slot_time.time()

        # Lunch block
        lunch_start = datetime.strptime("13:00", "%H:%M").time()
        lunch_end = datetime.strptime("14:00", "%H:%M").time()

        # If slot starts before or at work_start or ends after work_end -> outside hours
        slot_end_time = (datetime.combine(day_date.date(), slot_time_only) + timedelta(minutes=30)).time()

        if not (work_start <= slot_time_only < work_end) or not (work_start < slot_end_time <= work_end):
            return {"response": f"Sorry, {doctor} is not available at {slot} on {day} — that's outside of working hours ({schedules[day]['start_time']}–{schedules[day]['end_time']}). Would you like another time?"}

        if (lunch_start <= slot_time_only < lunch_end) or (lunch_start < slot_end_time <= lunch_end):
            return {"response": f"Sorry, {doctor} is not available at {slot} on {day} — that falls during our lunch break (13:00–14:00). Would you like a time before or after lunch?"}

        # Check for conflicts with existing appointments
        appointments = load_json(APPOINTMENTS_FILE)
        for appointment in appointments:
            appt_start = datetime.fromisoformat(appointment["start_time"])
            appt_end = datetime.fromisoformat(appointment["end_time"])
            if appt_start.date() == day_date.date():
                # overlap check
                if not (end_datetime <= appt_start or start_datetime >= appt_end):
                    return {"response": f"Sorry, {doctor} already has an appointment at {slot} on {day} (the 30-minute slot is taken). Would you like a different time?"}

        # All good — create appointment
        appointment_entry = {
            "name": name,
            "start_time": start_datetime.isoformat(),
            "end_time": end_datetime.isoformat()
        }

        print("\n" + "="*60)
        print("NEW APPOINTMENT BOOKED")
        print("="*60)
        print(f"Patient Name: {name}")
        print(f"Doctor: {doctor}")
        print(f"Day: {day}")
        print(f"Time Slot: {slot}")
        print(f"Date: {start_datetime.strftime('%Y-%m-%d')}")
        print(f"Duration: 30 minutes")
        print("="*60 + "\n")

        appointments.append(appointment_entry)
        save_json(APPOINTMENTS_FILE, appointments)
        formatted_date = format_date_ordinal(start_datetime)
        response = f"Perfect! I've booked your appointment with {doctor} on {formatted_date} at {slot}. Is there anything else I can help you with?"

        return {
            "response": response,
            "status": "success",
            "appointment": appointment_entry
        }
    
    except Exception as e:
        print(f"Error in book_appointment webhook: {e}")
        return {
            "response": "I'm having trouble booking the appointment right now. Please try again or call us directly."
        }


if __name__ == "__main__":
    import uvicorn
    print("Starting Clinic Voice Agent Backend...")
    print("API Documentation: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)
