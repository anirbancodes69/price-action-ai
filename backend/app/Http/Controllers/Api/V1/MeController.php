<?php

namespace App\Http\Controllers\Api\V1;

use App\Http\Controllers\Controller;
use App\Models\User;
use App\Support\ApiResponse;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class MeController extends Controller
{
    /**
     * UserSummary (OpenAPI). Profile fields are not stored yet (ARC-03 profile table is deferred), so they are null.
     *
     * @return array<string, mixed>
     */
    public static function summary(User $user): array
    {
        return [
            'id' => $user->getKey(),
            'email' => $user->email,
            'email_verified' => $user->email_verified_at !== null,
            'display_name' => null,
            'experience_level' => null,
            'timezone' => null,
        ];
    }

    public function show(Request $request): JsonResponse
    {
        /** @var User $user */
        $user = $request->user();

        return ApiResponse::ok(['user' => self::summary($user)]);
    }
}
