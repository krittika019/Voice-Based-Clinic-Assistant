
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
            slots_text = ", ".join(available_slots[:8])
            response = f"{doctor} is available on {day}. Here are some available time slots: {slots_text}. Which time works best for you?"
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
        
        if day not in schedules:
            return {
                "response": f"Sorry, the clinic is closed on {day}. Please choose a weekday or Saturday."
            }
        
        if schedules[day]["doctor"] != doctor:
            return {
                "response": f"{doctor} is not available on {day}. {schedules[day]['doctor']} is available that day."
            }
        
        day_date = get_day_date(day)
        slot_time = datetime.strptime(slot, "%H:%M")
        start_datetime = day_date.replace(
            hour=slot_time.hour,
            minute=slot_time.minute,
            second=0,
            microsecond=0
        )
        end_datetime = start_datetime + timedelta(minutes=30)
        
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
        
        appointments = load_json(APPOINTMENTS_FILE)
        appointments.append(appointment_entry)
        save_json(APPOINTMENTS_FILE, appointments)
        
        response = f"Perfect! I've booked your appointment with {doctor} on {day} at {slot}. Your appointment is confirmed for {start_datetime.strftime('%B %d')}. Is there anything else I can help you with?"
        
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
