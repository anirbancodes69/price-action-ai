<?php

return [

    /*
    |--------------------------------------------------------------------------
    | Third Party Services
    |--------------------------------------------------------------------------
    |
    | This file is for storing the credentials for third party services such
    | as Resend, Postmark, AWS, and more. This file provides the de facto
    | location for this type of information, allowing packages to have
    | a conventional file to locate the various service credentials.
    |
    */

    'postmark' => [
        'key' => env('POSTMARK_API_KEY'),
    ],

    'resend' => [
        'key' => env('RESEND_API_KEY'),
    ],

    'ses' => [
        'key' => env('AWS_ACCESS_KEY_ID'),
        'secret' => env('AWS_SECRET_ACCESS_KEY'),
        'region' => env('AWS_DEFAULT_REGION', 'us-east-1'),
    ],

    'slack' => [
        'notifications' => [
            'bot_user_oauth_token' => env('SLACK_BOT_USER_OAUTH_TOKEN'),
            'channel' => env('SLACK_BOT_USER_DEFAULT_CHANNEL'),
        ],
    ],

    // Internal Python engine (docs/architecture/08_INTEGRATION_ARCHITECTURE.md §5)
    'engine' => [
        'url' => env('ENGINE_URL', 'http://engine:8100'),
        'token' => env('ENGINE_SERVICE_TOKEN'),
        'timeout' => (float) env('ENGINE_TIMEOUT_SECONDS', 2),
        // A scan or analysis reads stored bars and analyses up to the whole universe.
        'scan_timeout' => (float) env('ENGINE_SCAN_TIMEOUT_SECONDS', 15),
        // The data_sources row the owner reads (empty: the DEMO source).
        'data_source_id' => env('ENGINE_DATA_SOURCE_ID', ''),
    ],

];
