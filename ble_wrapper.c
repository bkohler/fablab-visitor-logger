#include <stdlib.h>
#include <unistd.h>

int main() {
    // Execute the Python script with the current user's permissions
    char *args[] = {"python", "ble_wrapper.py", NULL};
    execvp(args[0], args);

    // If we get here, exec failed
    return 1;
}
