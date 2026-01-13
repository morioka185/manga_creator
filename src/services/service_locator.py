"""サービスロケータパターンによる依存性注入基盤

テスト時にモックサービスを注入可能にすることで、
テスト容易性を向上させる。

使用例:
    # プロダクションコード
    locator = ServiceLocator.get_instance()
    settings = locator.get(SettingsService)

    # テストコード
    ServiceLocator.reset()
    locator = ServiceLocator.get_instance()
    locator.register(SettingsService, MockSettingsService())
"""
from typing import Dict, Type, TypeVar, Optional


T = TypeVar('T')


class ServiceLocator:
    """サービスロケータ（シングルトン）

    サービスの登録と取得を一元管理する。
    既存のシングルトンサービスとの後方互換性を維持しつつ、
    テスト時にはモックサービスを注入可能。
    """

    _instance: Optional['ServiceLocator'] = None
    _services: Dict[Type, object]

    def __init__(self):
        self._services = {}

    @classmethod
    def get_instance(cls) -> 'ServiceLocator':
        """シングルトンインスタンスを取得"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls):
        """インスタンスをリセット（テスト用）

        テスト開始時に呼び出すことで、クリーンな状態から始められる。
        """
        cls._instance = None

    def register(self, service_type: Type[T], instance: T):
        """サービスを登録

        Args:
            service_type: サービスの型（クラス）
            instance: サービスのインスタンス
        """
        self._services[service_type] = instance

    def get(self, service_type: Type[T]) -> T:
        """サービスを取得

        登録済みのサービスがあればそれを返し、
        なければ既存のシングルトンパターン（get_instance()）を使用。

        Args:
            service_type: サービスの型（クラス）

        Returns:
            サービスのインスタンス
        """
        if service_type in self._services:
            return self._services[service_type]

        # 既存のシングルトンとの後方互換性
        if hasattr(service_type, 'get_instance'):
            return service_type.get_instance()

        raise ValueError(f"サービス {service_type.__name__} が登録されていません")

    def has(self, service_type: Type) -> bool:
        """サービスが登録されているか確認

        Args:
            service_type: サービスの型（クラス）

        Returns:
            登録済みならTrue
        """
        if service_type in self._services:
            return True
        # 既存シングルトンは常に利用可能とみなす
        return hasattr(service_type, 'get_instance')

    def unregister(self, service_type: Type):
        """サービスの登録を解除

        Args:
            service_type: サービスの型（クラス）
        """
        if service_type in self._services:
            del self._services[service_type]

    def register_defaults(self):
        """デフォルトサービスを登録

        アプリケーション起動時に呼び出す。
        既存のシングルトンサービスをそのまま使用する場合、
        明示的な登録は不要（get_instance()にフォールバック）。
        """
        # 現時点では既存のシングルトンにフォールバックするため、
        # 明示的な登録は不要。
        # 将来的にサービスの初期化順序を制御したい場合に使用。
        pass


# 便利関数
def get_service(service_type: Type[T]) -> T:
    """サービスを取得するショートカット関数

    Args:
        service_type: サービスの型（クラス）

    Returns:
        サービスのインスタンス

    使用例:
        settings = get_service(SettingsService)
    """
    return ServiceLocator.get_instance().get(service_type)
