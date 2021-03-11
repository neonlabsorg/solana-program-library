pragma solidity ^0.5.12;

contract callOtherContract {
    function callHelloWorld(address hello) public payable returns (string memory) {
        (bool status, bytes memory result) = hello.call(abi.encodeWithSignature("callHelloWorld()"));
        if (!status) {
            revert();
        }
        return abi.decode(result, (string));
    }
}