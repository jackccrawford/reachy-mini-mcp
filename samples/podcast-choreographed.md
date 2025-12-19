# Choreographed Podcast: Reachy Mini MCP

A sample choreographed performance using only **built-in emotions** (no audio in moves).

## Available Built-in Emotions (Silent)

These 12 emotions are motor-only poses with no embedded audio:
- `neutral`, `curious`, `uncertain`, `recognition`, `joy`
- `thinking`, `listening`, `agreeing`, `disagreeing`
- `sleepy`, `surprised`, `focused`

## The Script

```python
# Intro
speak("[move:listening] This is the brief on the Reachy Mini MCP. [move:curious] So, what exactly is the Reachy Mini MCP? [move:thinking] Well, it's basically the software bridge that gives large AI systems, you know, like GPT or Grok, a real physical body.")

speak("[move:joy] We're talking about the Pollen Robotics Reachy Mini Robot. [move:focused] The goal here is to let an AI actually speak, listen, see, and express emotion through physical movement.")

# Developer Simplicity
speak("[move:listening] All right, let's dive into what you really need to know. [move:recognition] First, it's all about developer simplicity. [move:surprised] You can seriously get a demo running in just 30 minutes with zero robotics expertise.")

speak("[move:thinking] That's because all control is boiled down to just seven core token efficient tools. [move:agreeing] This approach, which follows Miller's law, makes the whole system way more reliable and cheaper for the AI to operate.")

# Choreographed Speech
speak("[move:joy] Second, the interactions feel incredibly sophisticated. [move:recognition] The real magic is in something called choreographed speech. [move:focused] The speak function lets you embed move markers right into the AI's dialogue.")

speak("[move:agreeing] This means physical gestures and head movements can automatically sync up with what the AI is saying. [move:joy] The robot can even pull from built-in emotions or over 80 pre-recorded moves to be super expressive.")

# Architecture
speak("[move:listening] And finally, the architecture is designed for total accessibility. [move:thinking] The MCP server acts as the translator between the AI's brain and the robot's body. [move:neutral] It's local first, running right on your machine.")

speak("[move:surprised] And here's the kicker! [move:joy] The same server works whether you're using the physical hardware or a software simulator. [move:agreeing] That makes development seamless.")

# Closing
speak("[move:recognition] The Reachy Mini MCP is making sophisticated, expressive robotics a plug-and-play reality for modern AI systems! [move:joy]")
```

## Emotion Mapping Logic

| Content Type | Emotions Used |
|-------------|---------------|
| Questions | `curious`, `thinking` |
| Explanations | `thinking`, `focused` |
| Excitement/Key Points | `joy`, `surprised`, `recognition` |
| Agreement/Confirmation | `agreeing` |
| Listening/Attention | `listening` |
| Neutral/Reset | `neutral` |

## Notes

- Built-in emotions are motor-only (head pose + antenna position)
- No embedded audio = clean separation from TTS voice
- Faster execution than recorded moves (local, no HTTP fetch)
- Works in both simulator and hardware
