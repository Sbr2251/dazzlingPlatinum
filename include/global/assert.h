#ifndef POKEPLATINUM_ASSERT_H
#define POKEPLATINUM_ASSERT_H

/*
 * Assert statements. If the expression evaluates false,
 * the software will terminate.
 *
 * PM_KEEP_ASSERTS is defined in dev/asan builds and absent in release,
 * where GF_ASSERT compiles to nothing. On PC builds a failure prints
 * file:line, the expression and a symbolized backtrace, then exits 134
 * (in interactive runs it also writes log.txt and shows a message box).
 * See docs/headless_protocol.md.
 */
#ifdef PM_KEEP_ASSERTS
#define GF_ASSERT(expr) ((expr) ? (void)0 : ErrorHandling_AssertFail(__FILE__, __LINE__, #expr))
#else
#define GF_ASSERT(...) ((void)0)
#endif // PM_KEEP_ASSERTS

/*
 * void ErrorHandling_AssertFail(const char *file, int line, const char *expr)
 *
 * Called when an assertion fails.
 * Do not use this directly.
 * Instead, use the GF_ASSERT macro defined above.
 */
void ErrorHandling_AssertFail(const char *file, int line, const char *expr);

#endif // POKEPLATINUM_ASSERT_H
