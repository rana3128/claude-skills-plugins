# Execution context, call stack and strict mode
Source: Quick JS Node guide section 1
Tag: JS CORE
Key facts:
- Each context has a creation phase (memory set up) and an execution phase (run line by line)
- Contexts stack on the call stack; single thread means only the top runs
- Kinds: global, one per function call, one per eval
- Strict mode is automatic in ES modules and classes: no implicit globals, this undefined in plain calls, writes to read-only props throw

## How does JavaScript run your code?
Visual: title | Execution context, Call stack, Strict mode
- What actually happens when JavaScript runs your code, and what is an execution context?

## Two phases
Visual: flow | Creation phase [blue]: memory is set up | Execution phase [green]: code runs line by line
- An execution context is the environment a piece of code runs in. It holds that code's variables, its scope, and its value of this.
- Every context goes through two phases. First the creation phase. The engine scans the code and sets up memory for its variables and functions, before running a single line.
- Then the execution phase. The code runs line by line, and values get assigned.
- This two step process is why hoisting exists, because names are known before the code runs.

## Three kinds of context
Visual: cards | Global [blue]: created once at the start | Function [green]: a new one for every call | Eval [red]: one for each eval
- There are three kinds. One global context is created when the script starts.
- Then a brand new function context is created for every single call. Call the same function three times, and you get three separate contexts, each with its own variables.
- And eval gets its own context, though you should rarely use it.

## The call stack
Visual: flow | global [dim] | main [blue] | fetchUser [green] | parse [orange]
- Contexts live on the call stack. Say the global code calls main, main calls fetch user, and fetch user calls parse. Each call pushes a new context on top.
- JavaScript has a single thread, so only the top of the stack runs. Main is frozen until everything above it finishes.
- When parse returns, its context pops off, and fetch user continues exactly where it stopped.
- If a function keeps calling itself with no exit, the stack overflows and you get a range error.

## Strict mode
Visual: cards | No implicit globals [green] | this is undefined in plain calls [blue] | Read-only writes throw [red]
- Strict mode changes some of these rules, and it is automatic inside E S modules and classes.
- Assigning to an undeclared name throws an error, instead of silently creating a global.
- The value of this is undefined in a plain function call.
- And writing to a read only property throws, instead of failing silently. Strict mode turns silent bugs into loud errors, and that is why you want it.
