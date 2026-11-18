<?php

return [
    // Planning capital used for scan sizing until the risk profile endpoints exist (ADR-014 planning value, HYPOTHESIS).
    'capital' => env('TRADING_CAPITAL_DEFAULT', '100000'),
];
