from webcompy.di import DIScope, InjectionError, InjectKey, inject, provide
from webcompy.di._scope import _MISSING


class TestInjectKey:
    def test_identity_uniqueness(self):
        key1 = InjectKey("same-name")
        key2 = InjectKey("same-name")
        assert key1 is not key2
        assert key1 != key2

    def test_repr_shows_name(self):
        key = InjectKey("my-service")
        assert "my-service" in repr(key)

    def test_hash_based_on_identity(self):
        key1 = InjectKey("a")
        key2 = InjectKey("b")
        d = {key1: "val1", key2: "val2"}
        assert d[key1] == "val1"
        assert d[key2] == "val2"

    def test_generic_type_annotation(self):
        ApiKey = InjectKey[str]("api-key")
        assert ApiKey.name == "api-key"


class TestDIScope:
    def test_creation_and_provide_inject(self):
        scope = DIScope()
        key = InjectKey[str]("test-key")
        scope.provide(key, "hello")
        assert scope.inject(key) == "hello"

    def test_creation_with_initial_providers(self):
        key = InjectKey[str]("test-key")
        scope = DIScope({key: "hello"})
        assert scope.inject(key) == "hello"

    def test_parent_chain_resolution(self):
        parent = DIScope()
        key = InjectKey[str]("test-key")
        parent.provide(key, "from-parent")
        child = DIScope(parent=parent)
        assert child.inject(key) == "from-parent"

    def test_child_shadows_parent(self):
        parent = DIScope()
        key = InjectKey[str]("test-key")
        parent.provide(key, "from-parent")
        child = DIScope(parent=parent)
        child.provide(key, "from-child")
        assert child.inject(key) == "from-child"

    def test_inject_raises_on_missing_key(self):
        scope = DIScope()
        key = InjectKey[str]("test-key")
        try:
            scope.inject(key)
            raise AssertionError("Should have raised InjectionError")
        except InjectionError:
            pass

    def test_inject_returns_default(self):
        scope = DIScope()
        key = InjectKey[str]("test-key")
        assert scope.inject(key, default="fallback") == "fallback"

    def test_inject_returns_none_default(self):
        scope = DIScope()
        key = InjectKey[str]("test-key")
        assert scope.inject(key, default=None) is None

    def test_class_type_key(self):
        class MyService:
            pass

        scope = DIScope()
        svc = MyService()
        scope.provide(MyService, svc)
        assert scope.inject(MyService) is svc

    def test_context_manager(self):
        key = InjectKey[str]("test-key")
        scope = DIScope({key: "hello"})
        with scope:
            assert inject(key) == "hello"
        try:
            inject(key)
            raise AssertionError("Should have raised InjectionError")
        except InjectionError:
            pass

    def test_nested_context_managers(self):
        outer_key = InjectKey[str]("outer")
        inner_key = InjectKey[str]("inner")
        outer = DIScope({outer_key: "outer-val"})
        inner = DIScope(parent=outer)
        inner.provide(inner_key, "inner-val")
        with outer:
            assert inject(outer_key) == "outer-val"
            with inner:
                assert inject(inner_key) == "inner-val"
                assert inject(outer_key) == "outer-val"
            assert inject(outer_key) == "outer-val"

    def test_create_child(self):
        parent = DIScope()
        key = InjectKey[str]("test-key")
        parent.provide(key, "from-parent")
        child = parent.create_child()
        assert child.inject(key) == "from-parent"

    def test_dispose(self):
        scope = DIScope()
        key = InjectKey[str]("test-key")
        scope.provide(key, "hello")
        scope.dispose()
        try:
            scope.inject(key)
            raise AssertionError("Should have raised InjectionError")
        except InjectionError:
            pass

    def test_dispose_propagates_to_children(self):
        parent = DIScope()
        key = InjectKey[str]("test-key")
        parent.provide(key, "hello")
        child = parent.create_child()
        parent.dispose()
        try:
            child.inject(key)
            raise AssertionError("Should have raised InjectionError")
        except InjectionError:
            pass

    def test_factory_lazy_instantiation(self):
        scope = DIScope()
        key = InjectKey[str]("test-key")
        calls = {"count": 0}

        def factory():
            calls["count"] += 1
            return "lazy-value"

        scope.provide(key, factory)
        assert calls["count"] == 0
        assert scope.inject(key) == "lazy-value"
        assert calls["count"] == 1
        assert scope.inject(key) == "lazy-value"
        assert calls["count"] == 1

    def test_dispose_raises_on_provide(self):
        scope = DIScope()
        scope.dispose()
        key = InjectKey[str]("test-key")
        try:
            scope.provide(key, "value")
            raise AssertionError("Should have raised RuntimeError")
        except RuntimeError:
            pass

    def test_dispose_creates_child_raises(self):
        scope = DIScope()
        scope.dispose()
        try:
            scope.create_child()
            raise AssertionError("Should have raised RuntimeError")
        except RuntimeError:
            pass


class TestModuleLevelFunctions:
    def test_provide_and_inject(self):
        key = InjectKey[str]("test-key")
        scope = DIScope({key: "hello"})
        with scope:
            assert inject(key) == "hello"

    def test_provide_in_context_manager(self):
        key = InjectKey[str]("test-key")
        scope = DIScope()
        with scope:
            provide(key, "hello")
            assert inject(key) == "hello"

    def test_inject_raises_outside_scope(self):
        key = InjectKey[str]("test-key")
        try:
            inject(key)
            raise AssertionError("Should have raised InjectionError")
        except InjectionError:
            pass

    def test_inject_default_outside_scope(self):
        key = InjectKey[str]("test-key")
        assert inject(key, default="fallback") == "fallback"

    def test_injection_error_message(self):
        key = InjectKey[str]("my-service")
        try:
            inject(key)
            raise AssertionError("Should have raised InjectionError")
        except InjectionError as e:
            assert "my-service" in str(e)

    def test_injection_error_message_class_key(self):
        class MyService:
            pass

        try:
            inject(MyService)
            raise AssertionError("Should have raised InjectionError")
        except InjectionError as e:
            assert "MyService" in str(e)

    def test_overwrite_provide(self):
        key = InjectKey[str]("test-key")
        scope = DIScope()
        with scope:
            provide(key, "first")
            assert inject(key) == "first"
            provide(key, "second")
            assert inject(key) == "second"

    def test_lazy_child_scope_creation_via_provide(self):
        parent = DIScope()
        parent_key = InjectKey[str]("parent-key")
        child_key = InjectKey[str]("child-key")
        parent.provide(parent_key, "from-parent")
        with parent:
            assert inject(parent_key) == "from-parent"
            provide(child_key, "from-child")
            assert inject(child_key) == "from-child"
            assert inject(parent_key) == "from-parent"

    def test_missing_sentinel(self):
        assert _MISSING is not None
        assert _MISSING is not False
