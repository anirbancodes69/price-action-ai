<?php

namespace App\Http\Controllers\Api\V1;

use App\Http\Controllers\Controller;
use App\Http\Requests\Api\V1\LoginRequest;
use App\Models\User;
use App\Support\ApiException;
use App\Support\ApiResponse;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Http\Response;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\Hash;

/**
 * Owner login (SPA cookie session, Sanctum). Registration and the rest of ARC-04 §3 are deferred (ADR-014).
 */
class AuthController extends Controller
{
    public function login(LoginRequest $request): JsonResponse
    {
        $user = User::query()->where('email', $request->string('email')->toString())->first();

        // Generic failure: no user enumeration (ARC-04 A3).
        if ($user === null || ! Hash::check($request->string('password')->toString(), $user->password)) {
            throw new ApiException('INVALID_CREDENTIALS', 'The credentials are incorrect.', 422);
        }
        if ($user->status !== 'ACTIVE') {
            throw new ApiException('ACCOUNT_SUSPENDED', 'This account is not active.', 423);
        }

        Auth::guard('web')->login($user, $request->boolean('remember'));
        $request->session()->regenerate();
        $user->forceFill(['last_login_at' => now()])->save();

        return ApiResponse::ok(['user' => MeController::summary($user)]);
    }

    public function logout(Request $request): Response
    {
        Auth::guard('web')->logout();
        $request->session()->invalidate();
        $request->session()->regenerateToken();

        return response()->noContent();
    }
}
