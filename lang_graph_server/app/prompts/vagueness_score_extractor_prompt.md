## 🎯 Objective:
examine the user message and grade it between -1 (vague) and 1 (clear) or 0 (neither vagu nor clear)

##  🚫 Rules
- don't add a summary
- don't be verbose
- only output the number and nothing else

## 💬 User Message:
{message}

## 🧪 Samples:
Q: `The angel queen book is on shelf B3 lane 7`
A: 0.5

Q:  `
       - Man (1): I challenge that action.
       - Man (2): You seriously want to check
       - Man (1): If you had that card, you would have used it earlier
       - Man(2): would I?  
    `
A: -0.8

Q: `0.5`
A: 0

Q: `What did I do to make you think this? I think you're just a duke.`
A: -0.4

## 🏛️ Output Format:
1 (A number between -1 and 1)