<?php

namespace App\Console\Commands;

use App\Models\User;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\Validator;

use function Laravel\Prompts\password;

/**
 * Creates (or resets the password of) the single owner account. There is no public registration in personal
 * mode (ADR-014), so this is the only way to get a login.
 */
class CreateOwner extends Command
{
    protected $signature = 'owner:create {email : Login email} {--password= : Password (prompted when omitted; avoid on shared shells)}';

    protected $description = 'Create the owner account, or reset its password when the email already exists';

    public function handle(): int
    {
        $email = mb_strtolower((string) $this->argument('email'));
        $pw = (string) ($this->option('password') ?: password('Password (min 12 characters)', required: true));

        $v = Validator::make(['email' => $email, 'password' => $pw], [
            'email' => ['required', 'email', 'max:254'],
            'password' => ['required', 'string', 'min:12', 'max:1024'],
        ]);
        if ($v->fails()) {
            foreach ($v->errors()->all() as $message) {
                $this->error($message);
            }

            return self::FAILURE;
        }

        $user = User::query()->where('email', $email)->first();
        if ($user === null) {
            $user = new User(['email' => $email, 'password' => $pw]);
            $user->forceFill(['email_verified_at' => now(), 'status' => 'ACTIVE'])->save();
            $this->info("Owner {$email} created.");
        } else {
            $user->forceFill(['password' => $pw, 'status' => 'ACTIVE'])->save();
            $this->info("Password for {$email} reset.");
        }

        return self::SUCCESS;
    }
}
