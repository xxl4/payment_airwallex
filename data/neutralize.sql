-- disable airwallex payment provider
UPDATE payment_provider
   SET airwallex_email_account = NULL,
       airwallex_client_id = NULL,
       airwallex_client_secret = NULL;
