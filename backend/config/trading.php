<?php

return [
    // Planning capital used for scan sizing until the risk profile endpoints exist (ADR-014 planning value, HYPOTHESIS).
    'capital' => env('TRADING_CAPITAL_DEFAULT', '100000'),

    // Universe the scanner reads when the request names none (DEMO data source: set DEMO).
    'universe' => env('TRADING_UNIVERSE', 'NIFTY50'),
];
