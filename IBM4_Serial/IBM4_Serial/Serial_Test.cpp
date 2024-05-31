// Serial_Test.cpp : This file contains the 'main' function. Program execution begins and ends there.
#pragma once

#include <iostream>
#include <windows.h>
#include <string>

int main()
{
    std::cout << "Hello World!\n";
    std::wstring Port = L"COM4";

    HANDLE h_Serial;
    h_Serial = CreateFile((LPCWSTR)Port.c_str(), GENERIC_READ | GENERIC_WRITE, 0, 0, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, 0);
    if (h_Serial == INVALID_HANDLE_VALUE) {
        if (GetLastError() == ERROR_FILE_NOT_FOUND) {
        }
        std::wcout << "Port: " << Port << " was not found" << std::endl;
        return(0);
    }
    else {
        std::wcout << "Port: " << Port << " was opened" << std::endl;
    }

    DCB dcbSerialParam = { 0 };
    dcbSerialParam.DCBlength = sizeof(dcbSerialParam);

    if (!GetCommState(h_Serial, &dcbSerialParam)) {
        std::cout << "Get Comm State Failed" << std::endl;
    }
    else {
        std::cout << "Get Comm State: " << dcbSerialParam.BaudRate << std::endl;
    }

    dcbSerialParam.BaudRate = CBR_9600;
    dcbSerialParam.ByteSize = 8;
    dcbSerialParam.StopBits = ONESTOPBIT;
    dcbSerialParam.Parity = NOPARITY;

    if (!SetCommState(h_Serial, &dcbSerialParam)) {
        std::cout << "Set Comm State Failed" << std::endl;
    }
    else {
        std::cout << "Set Comm State Succeeded" << std::endl;
    }

    COMMTIMEOUTS timeout = { 0 };
    timeout.ReadIntervalTimeout = 60;
    timeout.ReadTotalTimeoutConstant = 60;
    timeout.ReadTotalTimeoutMultiplier = 15;
    timeout.WriteTotalTimeoutConstant = 60;
    timeout.WriteTotalTimeoutMultiplier = 8;
    if (!SetCommTimeouts(h_Serial, &timeout)) {
        std::cout << "Set Timeout Failed" << std::endl;
    }
    else {
        std::cout << "Set Timeout Succeeded" << std::endl;
    }

    const int n = 100;
    char sBuff[n + 1] = { 0 };
    DWORD dwRead = 0;
    DWORD dwWritten = 0;

    if (!WriteFile(h_Serial, "*IDN\r\n", 6, &dwWritten, NULL)) {
        std::cout << "Write function failed!\n";
    }
    else {
        std::cout << "Bytes Sent: " << dwWritten << std::endl;
    }

    if (!ReadFile(h_Serial, sBuff, n, &dwRead, NULL)) {
        std::cout << "Read function failed!\n";
    }
    else {
        std::cout << "Read(" << dwRead << "): " << sBuff << std::endl;
    }


    CloseHandle(h_Serial);
    std::wcout << "Port: " << Port << " was closed" << std::endl;
}

