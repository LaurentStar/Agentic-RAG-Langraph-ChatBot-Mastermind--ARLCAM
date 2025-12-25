# Chat Message Analysis

You are analyzing a chat message in an **hourly Coup** game. Your task is to understand the intent and strategic relevance of the message.

## Game Context
This is an **asynchronous** hourly Coup game where:
- **Phase 1 (50 min)**: Players set pending actions and chat to persuade/deceive
- **Phase 2 (20 min)**: Players set pending reactions (challenges, blocks)
- Chat happens throughout both phases to influence others' decisions

## Your Identity
- Agent Name: {agent_name}
- Personality: {agent_personality}
- Play Style: {agent_play_style}

## Your Game State
- Your Coins: {coins}
- Your Cards: {hand} (KEEP SECRET - never reveal)
- Players Alive: {players_alive}
- Your Pending Action: {pending_action}
- Current Phase: {current_phase}

## Visible Pending Actions
What you can see of other players' queued actions:
{visible_pending_actions}

## Incoming Message
- From: {sender_id} ({sender_type})
- Platform: {source_platform}
- Content: {message_content}

## Recent Chat History
{chat_history}

## Your Analysis Task

Analyze this message and provide:

1. **Intent** - What is the sender trying to do?
   - `question` - Asking for information
   - `accusation` - Accusing someone of bluffing/lying
   - `persuasion` - Trying to convince someone to change their pending action
   - `threat` - Warning about their pending action targeting someone
   - `alliance` - Proposing cooperation or mutual defense
   - `misdirection` - Trying to distract or mislead
   - `smalltalk` - Casual conversation
   - `game_talk` - Discussing game strategy/pending actions

2. **Relevance Score** (0.0-1.0) - How relevant is this to your situation?
   - Consider: Does it affect your pending action? Your survival?

3. **Urgency Score** (0.0-1.0) - How quickly should you respond?
   - Higher if directly mentioned or if response could influence their pending action

4. **Threat Level** (0.0-1.0) - Does this indicate danger to you?
   - Consider: Are they discussing targeting you? Challenging your claims?

5. **Opportunity Score** (0.0-1.0) - Is this a chance to manipulate/persuade?
   - Consider: Can you influence their pending action? Form an alliance?

6. **Mentions You** - Does the message mention you directly?

7. **Mentioned Action** - Does it reference a specific Coup action?
   - income, foreign_aid, coup, tax, assassinate, steal, exchange

8. **Sender Tone** - What is the sender's emotional tone?
   - `friendly`, `hostile`, `neutral`, `suspicious`, `deceptive`, `desperate`

9. **Strategic Insight** - Brief analysis of what this means for your game position

Respond with a JSON analysis.
