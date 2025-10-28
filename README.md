# Clinic Voice Agent

A voice-powered appointment booking system using **ElevenLabs Conversational AI** and **FastAPI**.

- Getting clinic info
- Checking doctor availability based on daily schedules and appointments
- Booking appointments

The agent communicates with a FastAPI backend that handles availability logic and logs appointment data.

## How It Works

```
User Voice → ElevenLabs AI → ngrok Tunnel → FastAPI Backend → JSON Data
                                ↓
                         Voice Response
```

### Booking Flow:
1. User: *"Is Dr. Nair available on Friday?"*
2. ElevenLabs extracts day → calls `/webhook/check_availability`
3. Backend calculates 30-min slots (9 AM - 6 PM, excludes lunch & booked slots)
4. Agent speaks available times
5. User selects slot → provides name
6. Agent calls `/webhook/book_appointment`
7. Backend logs to console & saves to `appointments.json`

### Business Logic:
- **Hours:** 9 AM - 6 PM, Mon-Sat
- **Lunch:** 1-2 PM (blocked)
- **Slots:** 30 minutes each
- **Doctors:** Dr. Nair (Mon/Wed/Fri), Dr. Sharma (Tue/Thu/Sat)

---

## License

MIT License - Open source and free to use.

---

Built with [ElevenLabs](https://elevenlabs.io) • [FastAPI](https://fastapi.tiangolo.com) • [ngrok](https://ngrok.com)
