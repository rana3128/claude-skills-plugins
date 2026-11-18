# Lexical scope, closures and closure leaks
Source: Quick JS Node guide section 2
Tag: JS CORE
Key facts:
- Lexical scope: a function sees variables where it was written, not where called
- Closure = function + live reference to its creation scope; closures capture bindings, not values
- Uses: data privacy, module pattern, factories, currying, debounce, throttle, memoize, callbacks, React stale closures
- Trap: msg changed after the arrow was made: arrow logs the new value
- Trap: long-lived listeners, caches, timers keep scope alive; remove listeners, clear timers, do not capture big objects

## What is a closure?
Visual: title | Lexical scope, Closure, Memory leaks
- What is a closure, and why does it remember variables after the outer function has finished?

## Lexical scope
Visual: cards | Where it was written [green]: decides what it sees | Where it was called [red]: does not matter
- It starts with lexical scope. A function sees the variables around the place where it was written, not the place where it was called.
- So if you define a function inside a module, and call it from a completely different file, it still reads variables from its home module. The location in the source code decides everything.

## A function plus its scope
Visual: stack | function counter() | let count = 0 | return () => ++count
- A closure is a function, plus a live reference to the scope it was created in.
- Take a counter function. It declares count, set to zero, and returns an inner arrow that adds one to count.
- When counter returns, its context leaves the stack. But count is not destroyed, because the inner function still refers to it.
- Each call to the returned function keeps adding to that same count. And nobody outside can touch it. That is real privacy.

## Bindings, not values
Visual: flow | msg = hello [blue] | Arrow created [green] | msg = bye [orange] | Arrow logs bye [red]
- Here is the key detail. Closures capture bindings, not values. A binding is the variable itself, not a snapshot of what it held.
- Set message to hello, and create an arrow that logs it. Then change message to bye, and call the arrow. It logs bye, the new value. The arrow reads the live variable when it runs.

## Where you use them
Visual: grid | Data privacy [green] | Factories and currying [blue] | Debounce and memoize [orange] | Callbacks [teal]
- You use closures constantly. Data privacy and the module pattern. Factories and currying. Debounce, throttle and memoize, which all hide a timer or a cache in a closure. Every callback, and even stale closures in React.

## Can closures leak memory?
Visual: cards | Long-lived listeners [red] | Caches and timers [red] | Remove and clear [green]
- Can closures leak memory? Yes. A long lived listener, cache or timer keeps its whole scope alive, along with any big object in it.
- The fix is to remove listeners, clear timers, and avoid capturing big objects you do not need.
