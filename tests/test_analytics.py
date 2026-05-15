from src.models.analytics import OrderFlow


def test_put_call_ratio_returns_none_when_call_volume_zero():
    flow = OrderFlow(call_volume=0, put_volume=10)

    assert flow.put_call_ratio is None


def test_put_call_ratio_returns_value_when_call_volume_present():
    flow = OrderFlow(call_volume=4, put_volume=10)

    assert flow.put_call_ratio == 2.5
