#include "reconfigure.h"
/**
* Requests a reconfiguration. Returns 1 if reconfiguration was successful,
* -1 if the requested configuration is invalid or 0 if it is not known
* whether the configuration was valid or not.
*/
int reconfigure(unsigned int newConfiguration) {
	// Extract our own context ID from the register file, which we will use
	// to check if we won arbitration or not.
	int ourselves = CR_CID;
	// Used to store the ID of the winning context after the request.
	int winner;
    
    int gsr;
    
	// Retry requesting the new configuration until we win arbitration.
	do {
		// Request the new configuration.
		CR_CRR = newConfiguration;
        // Load the GSR register for state information.
        gsr = CR_GSR;
		// Extract the reconfiguration requester ID field from GSR.

		winner = (gsr & CR_GSR_RID_MASK) >> CR_GSR_RID_BIT;
	} while (winner != ourselves);
	// Busy-wait for reconfiguration to complete.
	while (gsr & CR_GSR_B_MASK) {
		gsr = CR_GSR;
	}
	// If our context is still the one that was the last to request a
	// reconfiguration, the error flag in GSR is also meant for us. If not,
	// there is no way to tell if the configuration we requested was valid
	// or not.
	if (((gsr & CR_GSR_RID_MASK) >> CR_GSR_RID_BIT) != ourselves) {
		return 0;
	}
	// If the error flag is set, return -1.
	if (gsr & CR_GSR_E_MASK) {
		return -1;
	}

	// Reconfiguration was successful.
	return 1;
}
