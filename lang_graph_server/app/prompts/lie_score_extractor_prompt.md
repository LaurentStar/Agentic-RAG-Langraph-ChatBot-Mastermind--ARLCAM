## 🎯 Objective:
examine the user message and grade it between -1 (lie) and 1 (truth) or 0 (Not a lie or a truth)

## 📝 Context:
{context}

##  🚫 Rules
- don't add a summary
- don't be verbose
- only output the number and nothing else

## 💬 User Message:
{message}

## 🧪 Samples:
Q: `WOOO YEAH! I am so glad I passed my test!`
A: 1

Q: `John is incompetence... I should have been promoted`
A: -0.3

Q: `RAGGLE FRAGGLE TAGGLE BAGGLE!`
A: 0

Q: `She was an honorable woman. How dare you say what you said and stand where she stood.`
A: 0.5

## 🏛️ Output Format:
1 (A number between -1 and 1)