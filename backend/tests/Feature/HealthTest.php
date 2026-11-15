<?php

namespace Tests\Feature;

use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Redis;
use RuntimeException;
use Tests\TestCase;

class HealthTest extends TestCase
{
    public function test_shallow_health_needs_no_dependencies(): void
    {
        $this->getJson('/api/health')
            ->assertOk()
            ->assertExactJson(['status' => 'ok', 'service' => 'backend']);
    }

    public function test_deep_health_reports_ok_when_all_dependencies_respond(): void
    {
        config(['services.engine.url' => 'http://engine.test', 'services.engine.token' => 'tkn']);
        DB::shouldReceive('select')->once()->andReturn([]);
        Redis::shouldReceive('connection->ping')->once()->andReturn(true);
        Http::fake(['engine.test/internal/v1/ping' => Http::response(['status' => 'ok'])]);

        $this->getJson('/api/health?deep=1')
            ->assertOk()
            ->assertJson(['status' => 'ok', 'checks' => ['database' => true, 'redis' => true, 'engine' => true]]);

        Http::assertSent(fn ($request) => $request->hasHeader('Authorization', 'Bearer tkn'));
    }

    public function test_deep_health_is_503_and_leaks_no_detail_when_a_dependency_fails(): void
    {
        DB::shouldReceive('select')->once()->andThrow(new RuntimeException('connection refused to db-host'));
        Redis::shouldReceive('connection->ping')->once()->andReturn(true);
        Http::fake(['*' => Http::response([], 401)]);

        $response = $this->getJson('/api/health?deep=1')
            ->assertStatus(503)
            ->assertJson(['status' => 'degraded', 'checks' => ['database' => false, 'redis' => true, 'engine' => false]]);

        $this->assertStringNotContainsString('db-host', $response->getContent());
    }

    public function test_root_returns_service_descriptor(): void
    {
        $this->getJson('/')->assertOk()->assertJson(['api' => '/api/v1']);
    }
}
