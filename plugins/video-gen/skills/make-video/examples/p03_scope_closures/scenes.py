"""p03 Lexical scope, closures and closure leaks: scenes in the kinetic design (DESIGN.md), declared as stage blocks."""
import kinetic as K
from kinetic import (CYAN, VIOLET, AMBER, GREEN, RED, WHITE, DIM, Track, Pipe, Rows, Code, Lanes, Bars, Ring, Fan, Chips, Big, Note)

SCENES = K.part("Closures", "JS CORE", [("closure", CYAN, "closure"), ("remember", VIOLET, "remember"), ("outer scope", GREEN, "outer")], [
    [Rows(("where it was written", "this decides what it sees", GREEN, "written", "ok"),
          ("where it was called", "this does not matter", RED, "called", "bad")),
     Fan(("module.js: secret", CYAN, "define"), ("defined here", GREEN, "module"), ("called elsewhere", AMBER, "call")),
     Note("the source location decides", GREEN, "location")],
    [Code(["function counter() {", "  let count = 0", "  return () => ++count", "}"], "counter.js", "counter",
          hl=[(1, AMBER, "count", "leaves"), (2, CYAN, ("returns", 1))]),
     Pipe(("stack", "counter() has left the stack", DIM, "leaves"), ("closure", "count survives: the inner function holds it", GREEN, "destroyed")),
     Big(("count = 1", AMBER, "each"), ("count = 2", AMBER, "adding"), ("private", GREEN, "privacy"), size=64)],
    [Note("a binding is the variable, not a snapshot", AMBER, "binding"),
     Code(["let msg = 'hello'", "const log = () => console.log(msg)", "msg = 'bye'", "log()  // bye"], "binding.js", ("set", 1),
          hl=[(0, CYAN, ("hello", 1), ("change", 1)), (2, AMBER, ("change", 1)), (3, GREEN, ("logs", 1))]),
     Big(("hello", CYAN, ("hello", 1)), ("bye", GREEN, ("change", 1))),
     Note("reads the live variable when it runs", GREEN, "live")],
    [Rows(("data privacy", "the module pattern", GREEN, "privacy"), ("factories, currying", "functions that build functions", CYAN, "factories"),
          ("debounce, memoize", "hide a timer or a cache", AMBER, "debounce"), ("callbacks", "every one is a closure", VIOLET, "callback"),
          ("React stale closures", "an old render's values", RED, "stale"))],
    [Pipe(("long-lived listener, cache, timer", "", RED, "long"), ("keeps its whole scope alive", "", AMBER, "keeps"), ("big object stays in memory", "", RED, "big")),
     Chips(("remove listeners", GREEN, "remove"), ("clear timers", GREEN, "clear"), ("capture less", GREEN, "avoid"))],
])
