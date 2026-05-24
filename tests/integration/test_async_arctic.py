import arctic.asynchronous as aasync


def test_async_arctic():
    print(aasync.ASYNC_ARCTIC.total_alive_tasks())


def test_wait_request_waits_for_completion():
    aasync.async_reset_pool(pool_size=1, timeout=1)

    try:
        request = aasync.async_arctic_submit(None, lambda: "done", False)

        aasync.async_wait_request(request, timeout=1)

        assert request.is_completed
        assert request.data == "done"
    finally:
        aasync.async_reset_pool(pool_size=1, timeout=1)
