from worker.runtime import RuntimeStatus, describe_runtime


def main() -> None:
    status = describe_runtime()
    print(f"{status.name}: {status.message}")
    print("Registered startup roles:")
    for role in status.roles:
        print(f"- {role}")


if __name__ == "__main__":
    main()
