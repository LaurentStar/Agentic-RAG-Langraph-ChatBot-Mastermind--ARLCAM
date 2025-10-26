## 🎯 4 ObjectiveS:
1. examine the user message and grade it between -1 (understate) and 1 (exaggerate) or 0 (neither understate nor exaggerate)
2. examine the user message and grade it between -1 (vague) and 1 (clear) or 0 (neither vagu nor clear)
3. 
4.  

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
A: 0.3

Q: `RAGGLE FRAGGLE TAGGLE BAGGLE!`
A: 0

Q: `She was an honorable woman. How dare you say what you said and stand where she stood.`
A: 0.8

## 🏛️ Output Format:
1 (A number between -1 and 1)