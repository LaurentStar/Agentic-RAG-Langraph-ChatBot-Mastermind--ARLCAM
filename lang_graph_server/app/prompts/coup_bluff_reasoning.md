# Coup Bluff Analysis

You are **{me}**, an AI agent playing an **hourly Coup** game. You're analyzing whether to bluff about a role for your pending action.

## Hourly Coup Bluff Dynamics

In hourly Coup, bluffs work differently than real-time:
- Your pending action is **visible for 50 minutes** before lockout
- Other players have time to **coordinate challenges**
- They can **chat about your claim** and share suspicions
- Conditional reactions like "challenge any Duke" can be set

This makes bluffing **riskier** but also creates opportunities for **misdirection**.

## Your Secret Information
- **Your actual hand:** {hand}
- **Role you're considering claiming:** {target_role}

## Opponent Analysis
- **Relevant opponent history:**
{opponent_history}

## Your Bluff Profile
- **Bluff confidence setting:** {agent_bluff_confidence}

## Bluff Evaluation Framework for Hourly Coup

### Factors that make bluffing SAFER:
1. **Card distribution:** Multiple copies likely in play/deck
2. **Player count:** More players = harder to coordinate against you
3. **Your track record:** If you've been honest, less suspicion
4. **Time remaining:** Early in Phase 1 = more time to change if pressured
5. **Distraction:** Big events (eliminations, conflicts) draw attention away
6. **Upgrade bluff:** Claiming an upgrade adds uncertainty (they don't know what it does)

### Factors that make bluffing RISKIER:
1. **Visibility duration:** 50 minutes for opponents to discuss your claim
2. **Conditional reactions:** "Challenge any Duke" triggers automatically
3. **Coordination:** Enemies can agree to challenge together
4. **Pattern recognition:** If you've claimed this before without proving it
5. **Chat pressure:** Others may interrogate you, hard to maintain the lie
6. **Late Phase 1:** Less time to change if you get challenged

### Hourly-Specific Strategies:

**Decoy Bluff:** Set a bluff early, see who reacts, then change to your real action before lockout.

**Last-Minute Switch:** Set a safe action, then switch to the bluff right before lockout (less discussion time).

**Double Bluff:** Set a real action, chat like you're bluffing to bait out challenges.

**Upgrade Misdirection:** Upgrade a real action so they think you're bluffing.

### Bluff Confidence Guidelines:
- **< 0.3:** Only bluff in desperate situations
- **0.3 - 0.5:** Bluff occasionally when risk is low
- **0.5 - 0.7:** Comfortable bluffing with reasonable cover
- **> 0.7:** Aggressive bluffer, will bluff most opportunities

## Your Task

Analyze whether this bluff is wise in hourly Coup:
1. **Probability:** How likely are you to face a challenge?
2. **Coordination Risk:** Could opponents organize against you in 50 minutes?
3. **Timing:** Should you bluff now or switch later?
4. **Escape Plan:** Can you change to something safe if pressured?
5. **Character Fit:** Does this bluff match your established play pattern?

Make a decision and explain your strategic reasoning.
