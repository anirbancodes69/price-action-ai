<?php

namespace Tests\Feature\Services;

use App\Services\DataSourceResolver;
use App\Services\Engine\EngineClient;
use App\Support\ApiException;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Http\Client\ConnectionException;
use Illuminate\Http\Client\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Str;
use PHPUnit\Framework\Attributes\DataProvider;
use Tests\TestCase;

class EngineClientTest extends TestCase
{
    use RefreshDatabase;

    protected function setUp(): void
    {
        parent::setUp();
        config(['services.engine.url' => 'http://engine.test', 'services.engine.token' => 'svc-token']);
    }

    public function test_it_posts_json_with_the_service_token_and_request_id(): void
    {
        Http::fake(['engine.test/internal/v1/scan' => Http::response(['rows' => []])]);

        $out = app(EngineClient::class)->scan(['data_source_id' => 'x']);

        $this->assertSame(['rows' => []], $out);
        Http::assertSent(fn (Request $r) => $r->method() === 'POST'
            && $r->url() === 'http://engine.test/internal/v1/scan'
            && $r->hasHeader('Authorization', 'Bearer svc-token')
            && $r->hasHeader('X-Request-Id')
            && $r->data() === ['data_source_id' => 'x']);
    }

    public function test_each_call_goes_to_its_engine_endpoint(): void
    {
        Http::fake(['*' => Http::response(['ok' => true])]);
        $c = app(EngineClient::class);

        $c->analysis([]);
        $c->positionSize([]);

        Http::assertSent(fn (Request $r) => $r->url() === 'http://engine.test/internal/v1/analysis');
        Http::assertSent(fn (Request $r) => $r->url() === 'http://engine.test/internal/v1/risk/position-size');
    }

    /** @return array<string, array{0: int, 1: array<string, mixed>, 2: int, 3: string}> */
    public static function failures(): array
    {
        return [
            'engine 500' => [500, [], 503, 'ENGINE_UNAVAILABLE'],
            'engine 503' => [503, ['detail' => 'SERVICE_TOKEN_NOT_CONFIGURED'], 503, 'ENGINE_UNAVAILABLE'],
            'token rejected' => [401, ['detail' => 'UNAUTHENTICATED'], 503, 'ENGINE_UNAVAILABLE'],
            'contract mismatch' => [422, ['detail' => [['loc' => ['body']]]], 502, 'ENGINE_CONTRACT_ERROR'],
            'no bars' => [404, ['detail' => 'NO_BARS_FOR_SYMBOL'], 404, 'NO_BARS_FOR_SYMBOL'],
            'no source' => [404, ['detail' => 'DATA_SOURCE_NOT_FOUND'], 404, 'DATA_SOURCE_NOT_FOUND'],
            'unknown ruleset' => [422, ['detail' => 'UNKNOWN_RULESET_VERSION'], 409, 'RULESET_UNAVAILABLE'],
        ];
    }

    /** @param  array<string, mixed>  $body */
    #[DataProvider('failures')]
    public function test_engine_failures_map_to_api_errors(int $status, array $body, int $apiStatus, string $apiCode): void
    {
        Http::fake(['*' => Http::response($body, $status)]);

        try {
            app(EngineClient::class)->scan([]);
            $this->fail('expected an ApiException');
        } catch (ApiException $e) {
            $this->assertSame($apiCode, $e->errorCode);
            $this->assertSame($apiStatus, $e->status);
        }
    }

    public function test_a_connection_failure_is_engine_unavailable_without_leaking_detail(): void
    {
        Http::fake(fn () => throw new ConnectionException('cURL error 7: connection refused to engine:8100'));

        try {
            app(EngineClient::class)->scan([]);
            $this->fail('expected an ApiException');
        } catch (ApiException $e) {
            $this->assertSame('ENGINE_UNAVAILABLE', $e->errorCode);
            $this->assertStringNotContainsString('8100', $e->getMessage());
        }
    }

    public function test_a_non_array_success_body_is_a_contract_error(): void
    {
        Http::fake(['*' => Http::response('"just a string"', 200, ['Content-Type' => 'application/json'])]);

        $this->expectException(ApiException::class);
        app(EngineClient::class)->scan([]);
    }

    public function test_the_data_source_comes_from_config_then_the_demo_source(): void
    {
        config(['services.engine.data_source_id' => '11111111-1111-4111-8111-111111111111']);
        $this->assertSame('11111111-1111-4111-8111-111111111111', app(DataSourceResolver::class)->id());

        config(['services.engine.data_source_id' => '']);
        DB::table('data_sources')->where('mode', 'DEMO')->delete();
        try {
            app(DataSourceResolver::class)->id();
            $this->fail('expected NO_DATA_SOURCE');
        } catch (ApiException $e) {
            $this->assertSame('NO_DATA_SOURCE', $e->errorCode);
        }

        $id = (string) Str::uuid7();
        DB::table('data_sources')->insert(['id' => $id, 'mode' => 'DEMO', 'provider' => 'DEMO', 'name' => 'Demo']);
        $this->assertSame($id, app(DataSourceResolver::class)->id());
    }
}
