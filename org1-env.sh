export TN=$HOME/hybrid-bench/fabric-samples/test-network
export FABRIC_CFG_PATH=$HOME/hybrid-bench/fabric-samples/config
export CORE_PEER_TLS_ENABLED=true
export CORE_PEER_LOCALMSPID=Org1MSP
export CORE_PEER_TLS_ROOTCERT_FILE=$TN/organizations/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/ca.crt
export CORE_PEER_MSPCONFIGPATH=$TN/organizations/peerOrganizations/org1.example.com/users/Admin@org1.example.com/msp
export CORE_PEER_ADDRESS=localhost:7051
export ORDERER_CA=$TN/organizations/ordererOrganizations/example.com/orderers/orderer.example.com/msp/tlscacerts/tlsca.example.com-cert.pem
export ORG1_TLS=$TN/organizations/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/ca.crt
export ORG2_TLS=$TN/organizations/peerOrganizations/org2.example.com/peers/peer0.org2.example.com/tls/ca.crt
hinvoke() { peer chaincode invoke -o localhost:7050 --ordererTLSHostnameOverride orderer.example.com --tls --cafile "$ORDERER_CA" -C mychannel -n hybrid --peerAddresses localhost:7051 --tlsRootCertFiles "$ORG1_TLS" --peerAddresses localhost:9051 --tlsRootCertFiles "$ORG2_TLS" --waitForEvent -c "$1"; }
hquery() { peer chaincode query -C mychannel -n hybrid -c "$1"; }
mt() { local L="$HOME/hybrid-bench/results/manual-tests.txt"; { echo; echo "\$ $*  # $(date -u +%FT%TZ)"; } | tee -a "$L"; "$@" 2>&1 | tee -a "$L"; return "${PIPESTATUS[0]}"; }
