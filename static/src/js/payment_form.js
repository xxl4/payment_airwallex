/* global airwallex */

import { loadJS } from '@web/core/assets';
import { _t } from '@web/core/l10n/translation';
import { rpc, RPCError } from '@web/core/network/rpc';

import paymentForm from '@payment/js/payment_form';

paymentForm.include({
    inlineFormValues: undefined,
    airwallexColor: 'blue',
    selectedOptionId: undefined,
    airwallexData: undefined,

    // #=== DOM MANIPULATION ===#

    /**
     * Hides airwallex button container if the expanded inline form is another provider.
     *
     * @private
     * @param {HTMLInputElement} radio - The radio button linked to the payment option.
     * @return {void}
     */
    async _expandInlineForm(radio) {
        const providerCode = this._getProviderCode(radio);
        if (providerCode !== 'airwallex') {
            document.getElementById('o_airwallex_button').classList.add('d-none');
        }
        this._super(...arguments);
    },
    /**
     * Prepare the inline form of Airwallex for direct payment.
     * The Airwallex sdk creates the payment button based on the client_id
     * and the currency of the order.
     * The created button is saved and reused when switching between different payment methods,
     * to avoid recreating the buttons.
     *
     * @override method from @payment/js/payment_form
     * @private
     * @param {number} providerId - The id of the selected payment option's provider.
     * @param {string} providerCode - The code of the selected payment option's provider.
     * @param {number} paymentOptionId - The id of the selected payment option
     * @param {string} paymentMethodCode - The code of the selected payment method, if any.
     * @param {string} flow - The online payment flow of the selected payment option.
     * @return {void}
     */
    async _prepareInlineForm(providerId, providerCode, paymentOptionId, paymentMethodCode, flow) {
        if (providerCode !== 'airwallex') {
            this._super(...arguments);
            return;
        }

        this._hideInputs();
        this._setPaymentFlow('direct');
        document.getElementById('o_airwallex_button').classList.remove('d-none');
        document.getElementById('o_airwallex_loading').classList.remove('d-none');
        // Check if instantiation of the component is needed.
        this.airwallexData ??= {}; // Store the component of each instantiated payment method.
        const currentAirwallexData = this.airwallexData[paymentOptionId]
        if (this.selectedOptionId && this.selectedOptionId !== paymentOptionId) {
            this.airwallexData[this.selectedOptionId]['airwallexButton'].hide()
        }
        if (currentAirwallexData && this.selectedOptionId !== paymentOptionId) {
            const airwallexSDKURL = this.airwallexData[paymentOptionId]['sdkURL']
            const airwallexButton = this.airwallexData[paymentOptionId]['airwallexButton']
            await loadJS(airwallexSDKURL);
            airwallexButton.show();
        }
        else if (!currentAirwallexData) {
            this.airwallexData[paymentOptionId] = {}
            const radio = document.querySelector('input[name="o_payment_radio"]:checked');
            if (radio) {
                this.inlineFormValues = JSON.parse(radio.dataset['airwallexInlineFormValues']);
                this.airwallexColor = radio.dataset['airwallexColor']
            }

            // https://developer.airwallex.com/sdk/js/configuration/#link-queryparameters
            const { client_id, currency_code } = this.inlineFormValues
            const airwallexSDKURL = `https://www.airwallex.com/sdk/js?client-id=${
                client_id}&components=buttons&currency=${currency_code}&intent=capture`
            await loadJS(airwallexSDKURL);
            const airwallexButton = airwallex.Buttons({ // https://developer.airwallex.com/sdk/js/reference
                fundingSource: airwallex.FUNDING.PAYPAL,
                style: { // https://developer.airwallex.com/sdk/js/reference/#link-style
                    color: this.airwallexColor,
                    label: 'airwallex',
                    disableMaxWidth: true,
                    borderRadius: 6,
                },
                createOrder: this._airwallexOnClick.bind(this),
                onApprove: this._airwallexOnApprove.bind(this),
                onCancel: this._airwallexOnCancel.bind(this),
                onError: this._airwallexOnError.bind(this),
            });
            this.airwallexData[paymentOptionId]['sdkURL'] = airwallexSDKURL;
            this.airwallexData[paymentOptionId]['airwallexButton'] = airwallexButton;
            airwallexButton.render('#o_airwallex_button');
        }
        document.getElementById('o_airwallex_loading').classList.add('d-none');
        this.selectedOptionId = paymentOptionId;
    },
    // #=== PAYMENT FLOW ===#

    /**
     * Handle the click event of the component and initiate the payment.
     *
     * @private
     * @return {void}
     */
    async _airwallexOnClick() {
        await this._submitForm(new Event("AirwallexClickEvent"));
        return this.airwallexData[this.selectedOptionId].airwallexOrderId;
    },

    _processDirectFlow(providerCode, paymentOptionId, paymentMethodCode, processingValues) {
        if (providerCode !== 'airwallex') {
            this._super(...arguments);
            return;
        }
        this.airwallexData[paymentOptionId].airwallexOrderId = processingValues['order_id'];
        this.airwallexData[paymentOptionId].airwallexTxRef = processingValues['reference'];
    },

    /**
     * Handle the approval event of the component and complete the payment.
     *
     * @private
     * @param {object} data - The data returned by Airwallex on approving the order.
     * @return {void}
     */
    async _airwallexOnApprove(data) {
        const orderID = data.orderID;
        const { provider_id } = this.inlineFormValues

        await rpc('/payment/airwallex/complete_order', {
            'provider_id': provider_id,
            'order_id': orderID,
            'reference': this.airwallexData[this.selectedOptionId].airwallexTxRef,
        }).then(() => {
            // Close the Airwallex buttons that were rendered
            this.airwallexData[this.selectedOptionId]['airwallexButton'].close();
            window.location = '/payment/status';
        }).catch(error => {
            if (error instanceof RPCError) {
                this._displayErrorDialog(_t("Payment processing failed"), error.data.message);
                this._enableButton(); // The button has been disabled before initiating the flow.
            }
            return Promise.reject(error);
        })
    },

    /**
     * Handle the cancel event of the component.
     * @private
     * @return {void}
     */
    _airwallexOnCancel() {
        this.call('ui', 'unblock');
    },

    /**
     * Handle the error event of the component.
     * @private
     * @param {object} error - The error in the component.
     * @return {void}
     */
    _airwallexOnError(error) {
        const message = error.message
        this.call('ui', 'unblock');
        // Airwallex throws an error if the popup is closed before it can load;
        // this case should be treated as an onCancel event.
        if (message !== "Detected popup close" && !(error instanceof RPCError)) {
            this._displayErrorDialog(_t("Payment processing failed"), message);
        }
    },
});
