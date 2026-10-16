/**
 * Session state shared between prototype screens (lives only in memory; nothing is stored).
 * Consent defaults follow report 06 §2.2.2: every outgoing data flow is off until the user opts in.
 */
export const proto = $state({
	telemetry: false,
	crashReports: false,
	aiNoticeDismissed: false,
	optimisationUndone: false
});
